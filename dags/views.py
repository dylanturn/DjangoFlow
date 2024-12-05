from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Avg
from .models import DAG, DAGRun, TaskInstance
from .statistics import TaskStatistics
from clusters.models import Cluster
from monitoring.models import Alert, Log
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

def dag_list(request):
    cluster_id = request.GET.get('cluster')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    dags = DAG.objects.all()
    
    if cluster_id:
        dags = dags.filter(cluster_id=cluster_id)
    
    if status:
        if status == 'active':
            dags = dags.filter(is_active=True)
        elif status == 'paused':
            dags = dags.filter(is_paused=True)
    
    if search:
        dags = dags.filter(Q(dag_id__icontains=search) | Q(description__icontains=search))
    
    # Annotate DAGs with run statistics
    dags = dags.annotate(
        total_runs=Count('runs'),
        running_runs=Count('runs', filter=Q(runs__state='running')),
        failed_runs=Count('runs', filter=Q(runs__state='failed'))
    )
    
    clusters = Cluster.objects.all()
    selected_cluster = None
    if cluster_id:
        selected_cluster = get_object_or_404(Cluster, id=cluster_id)
    
    # Print debug information
    print(f"Number of DAGs found: {dags.count()}")
    for dag in dags:
        print(f"DAG: {dag.dag_id}, Cluster: {dag.cluster.name}")
    
    context = {
        'dags': dags,
        'clusters': clusters,
        'selected_cluster': selected_cluster,
    }
    return render(request, 'dags/list.html', context)

def dag_details(request, id):
    try:
        dag = get_object_or_404(DAG, id=id)
        
        # Get recent runs
        recent_runs = dag.runs.all().order_by('-execution_date')[:5]
        
        # Get task statistics
        task_stats = TaskInstance.objects.filter(dag_run__dag=dag).values('task_id').annotate(
            total_runs=Count('id'),
            avg_duration=Avg('duration'),
            success_rate=Count('id', filter=Q(state='success')) * 100.0 / Count('id')
        )
        
        context = {
            'dag': dag,
            'recent_runs': recent_runs,
            'task_stats': task_stats,
        }
        return render(request, 'dags/detail.html', context)
    except DAG.DoesNotExist:
        raise Http404("DAG not found")

def dag_edit(request, id):
    dag = get_object_or_404(DAG, id=id)
            
    if request.method == 'POST':
        # Update DAG fields from form data
        dag.description = request.POST.get('description', '')
        dag.is_active = request.POST.get('is_active') == 'on'
        dag.is_paused = request.POST.get('is_paused') == 'on'
        dag.save()
        
        messages.success(request, 'DAG updated successfully.')
        return redirect('dags:details', id=dag.id)
    return render(request, 'dags/edit.html', {'dag': dag})

def dag_delete(request, id):
    dag = get_object_or_404(DAG, id=id)
            
    if request.method == 'POST':
        dag.delete()
        messages.success(request, 'DAG deleted successfully.')
        return redirect('dags:list')
    return render(request, 'dags/delete.html', {'dag': dag})

def dag_runs(request, id):
    try:
        dag = get_object_or_404(DAG, id=id)
        
        state = request.GET.get('state')
        runs = dag.runs.all()
        
        if state:
            runs = runs.filter(state=state)
        
        # Annotate runs with task statistics
        runs = runs.annotate(
            total_tasks=Count('task_instances'),
            failed_tasks=Count('task_instances', filter=Q(task_instances__state='failed')),
            success_tasks=Count('task_instances', filter=Q(task_instances__state='success')),
            running_tasks=Count('task_instances', filter=Q(task_instances__state='running'))
        )
        
        paginator = Paginator(runs, 20)  # Show 20 runs per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'dag': dag,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
        }
        return render(request, 'dags/runs.html', context)
    except DAG.DoesNotExist:
        raise Http404("DAG not found")

def run_detail(request, id, run_id):
    try:
        dag = get_object_or_404(DAG, id=id)
        run = get_object_or_404(DAGRun, dag=dag, run_id=run_id)
        
        # Get task instances for this run
        task_instances = run.task_instances.all()
        
        context = {
            'dag': dag,
            'run': run,
            'task_instances': task_instances,
        }
        return render(request, 'dags/run_detail.html', context)
    except (DAG.DoesNotExist, DAGRun.DoesNotExist):
        raise Http404("Run not found")

def dag_logs(request, id):
    dag = get_object_or_404(DAG, id=id)
    return render(request, 'dags/logs.html', {'dag': dag})

@login_required
@require_POST
def toggle_pause(request, id):
    dag = get_object_or_404(DAG, id=id)
    dag.is_paused = not dag.is_paused
    dag.save()
    
    return JsonResponse({
        'status': 'success',
        'is_paused': dag.is_paused
    })

@login_required
@require_POST
def trigger_dag(request, id):
    dag = get_object_or_404(DAG, id=id)
    
    # Create a new DAG run
    execution_date = timezone.now()
    run_id = f"manual__{execution_date.strftime('%Y-%m-%dT%H:%M:%S')}"
    
    dag_run = DAGRun.objects.create(
        dag=dag,
        run_id=run_id,
        execution_date=execution_date,
        state='running',
        external_trigger=True
    )
    
    return JsonResponse({
        'status': 'success',
        'run_id': dag_run.run_id,
        'execution_date': dag_run.execution_date.isoformat()
    })

def get_dag_schedules(request):
    """API endpoint to get DAG schedules for the timeline visualization."""
    try:
        date_str = request.GET.get('date')
        if date_str:
            base_date = timezone.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            base_date = timezone.now()

        # Get the start and end of the day
        start_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        # Get all active DAGs
        dags = DAG.objects.filter(is_active=True).select_related('cluster')
        
        schedules = []
        for dag in dags:
            # Get the next scheduled time based on the DAG's schedule interval
            if dag.schedule_interval:
                # Parse cron expression or interval string to get next run time
                next_run_time = dag.get_next_run_time(base_date)
                if next_run_time and start_date <= next_run_time <= end_date:
                    # Get the latest run status
                    latest_run = dag.runs.order_by('-execution_date').first()
                    status = latest_run.state if latest_run else 'scheduled'
                    
                    schedules.append({
                        'dag_id': dag.dag_id,
                        'start_time': next_run_time.isoformat(),
                        'schedule_interval': dag.schedule_interval,
                        'cluster': dag.cluster.name,
                        'status': status
                    })

        return JsonResponse({'schedules': schedules})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def dag_tasks(request, id):
    dag = get_object_or_404(DAG, id=id)
    task_type = request.GET.get('task_type')
    time_range = request.GET.get('time_range', '7')  # Default to 7 days
    
    # Initialize task statistics
    stats = TaskStatistics(
        dag=dag,
        time_range=timedelta(days=int(time_range))
    )
    
    # Get performance metrics and scheduler health
    performance_metrics = stats.get_performance_metrics()
    scheduler_health = stats.get_scheduler_health()
    task_trends = stats.get_task_trends()
    
    # Filter task instances if task_type is specified
    if task_type:
        performance_metrics = performance_metrics.filter(task_id__icontains=task_type)
    
    # Paginate results
    paginator = Paginator(list(performance_metrics), 20)  # Show 20 tasks per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique task types for filter dropdown
    task_types = TaskInstance.objects.filter(
        dag_run__dag=dag
    ).values_list('task_id', flat=True).distinct()
    
    context = {
        'dag': dag,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'task_types': task_types,
        'scheduler_health': scheduler_health,
        'task_trends': task_trends,
        'time_range': time_range,
    }
    return render(request, 'dags/tasks.html', context)
