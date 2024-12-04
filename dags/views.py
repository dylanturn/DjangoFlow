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

def dag_detail(request, dag_id):
    dag = get_object_or_404(DAG, id=dag_id)
    
    # Get recent runs
    recent_runs = dag.runs.all()[:5]
    
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

def dag_edit(request, dag_id):
    cluster_id = request.GET.get('cluster')
    if cluster_id:
        dag = get_object_or_404(DAG, dag_id=dag_id, cluster_id=cluster_id)
    else:
        dag = DAG.objects.filter(dag_id=dag_id).select_related('cluster').first()
        if not dag:
            raise Http404("DAG not found")
            
    if request.method == 'POST':
        # Update DAG fields from form data
        dag.description = request.POST.get('description', '')
        dag.is_active = request.POST.get('is_active') == 'on'
        dag.is_paused = request.POST.get('is_paused') == 'on'
        dag.save()
        
        messages.success(request, 'DAG updated successfully.')
        return redirect('dags:details', dag_id=dag.dag_id)
    return render(request, 'dags/edit.html', {'dag': dag})

def dag_delete(request, dag_id):
    cluster_id = request.GET.get('cluster')
    if cluster_id:
        dag = get_object_or_404(DAG, dag_id=dag_id, cluster_id=cluster_id)
    else:
        dag = DAG.objects.filter(dag_id=dag_id).select_related('cluster').first()
        if not dag:
            raise Http404("DAG not found")
            
    if request.method == 'POST':
        dag.delete()
        messages.success(request, 'DAG deleted successfully.')
        return redirect('dags:list')
    return render(request, 'dags/delete.html', {'dag': dag})

def dag_runs(request, dag_id):
    try:
        cluster_id = request.GET.get('cluster')
        if cluster_id:
            dag = get_object_or_404(DAG, dag_id=dag_id, cluster_id=cluster_id)
        else:
            # If no cluster specified, try to find the first matching DAG
            dag = DAG.objects.filter(dag_id=dag_id).first()
            if not dag:
                raise Http404("DAG not found")
        
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

def dag_tasks(request, dag_id):
    dag = get_object_or_404(DAG, id=dag_id)
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

def run_detail(request, dag_id, run_id):
    dag = get_object_or_404(DAG, id=dag_id)
    run = get_object_or_404(DAGRun, dag=dag, id=run_id)
    
    # Get task instances for this run
    task_instances = run.task_instances.all().order_by('task_id')
    
    context = {
        'dag': dag,
        'run': run,
        'task_instances': task_instances,
    }
    return render(request, 'dags/run_detail.html', context)

def dag_logs(request, dag_id):
    dag = get_object_or_404(DAG, id=dag_id)
    return render(request, 'dags/logs.html', {'dag': dag})

def dag_details(request, dag_id):
    try:
        cluster_id = request.GET.get('cluster')
        if cluster_id:
            dag = get_object_or_404(DAG, dag_id=dag_id, cluster_id=cluster_id)
        else:
            # If no cluster specified, try to find the first matching DAG
            dag = DAG.objects.filter(dag_id=dag_id).first()
            if not dag:
                raise Http404("DAG not found")
        
        recent_runs = dag.runs.order_by('-execution_date')[:10].prefetch_related('task_instances')
        
        # Process task instance counts for each run
        for run in recent_runs:
            task_counts = (
                run.task_instances
                .values('state')
                .annotate(count=Count('id'))
                .order_by('state')
            )
            run.task_state_counts = [
                {'state': item['state'], 'count': item['count']}
                for item in task_counts
            ]
        
        context = {
            'dag': dag,
            'recent_runs': recent_runs,
        }
        return render(request, 'dags/details.html', context)
    except DAG.DoesNotExist:
        raise Http404("DAG not found")

@login_required
@require_POST
def toggle_pause(request, dag_id):
    """Toggle the pause state of a DAG"""
    dag = get_object_or_404(DAG, dag_id=dag_id)
    dag.is_paused = not dag.is_paused
    dag.save()
    
    status = 'paused' if dag.is_paused else 'unpaused'
    messages.success(request, f'DAG {dag.dag_id} has been {status}')
    return JsonResponse({'status': 'success', 'is_paused': dag.is_paused})

@login_required
@require_POST
def trigger_dag(request, dag_id):
    """Manually trigger a DAG run"""
    dag = get_object_or_404(DAG, dag_id=dag_id)
    
    # Create a new DAG run
    run_id = f'manual__{timezone.now().strftime("%Y-%m-%dT%H:%M:%S")}'
    dag_run = DAGRun.objects.create(
        dag=dag,
        run_id=run_id,
        state='queued',
        execution_date=timezone.now(),
        external_trigger=True
    )
    
    messages.success(request, f'DAG {dag.dag_id} has been triggered')
    return JsonResponse({
        'status': 'success',
        'run_id': dag_run.run_id,
        'execution_date': dag_run.execution_date.isoformat()
    })
