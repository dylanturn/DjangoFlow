from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import Alert, Metric, Log
from clusters.models import Cluster
from dags.models import DAG, DAGRun, TaskInstance
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

def dashboard(request):
    # Get overall system stats
    clusters = Cluster.objects.annotate(
        total_dags=Count('dags'),
        active_dags=Count('dags', filter=Q(dags__is_active=True)),
        failed_tasks=Count(
            'dags__runs__task_instances',
            filter=Q(dags__runs__task_instances__state='failed')
        )
    )
    
    # Get recent alerts
    recent_alerts = Alert.objects.filter(
        is_resolved=False
    ).order_by('-created_at')[:5]
    
    # Get system metrics for the last 24 hours
    last_24h = timezone.now() - timedelta(hours=24)
    system_metrics = Metric.objects.filter(
        timestamp__gte=last_24h
    ).order_by('-timestamp')
    
    # Get recent logs
    recent_logs = Log.objects.order_by('-timestamp')[:10]
    
    context = {
        'clusters': clusters,
        'recent_alerts': recent_alerts,
        'system_metrics': system_metrics,
        'recent_logs': recent_logs,
    }
    return render(request, 'monitoring/dashboard.html', context)

def health_check(request):
    clusters = Cluster.objects.all()
    health_data = []
    
    for cluster in clusters:
        # Get last hour metrics
        last_hour = timezone.now() - timedelta(hours=1)
        metrics = Metric.objects.filter(
            cluster=cluster,
            timestamp__gte=last_hour
        ).order_by('-timestamp')
        
        # Calculate health score based on metrics and recent failures
        failed_tasks = TaskInstance.objects.filter(
            dag_run__dag__cluster=cluster,
            state='failed',
            end_date__gte=last_hour
        ).count()
        
        health_data.append({
            'cluster': cluster,
            'metrics': metrics,
            'failed_tasks': failed_tasks,
            'last_updated': metrics.first().timestamp if metrics.exists() else None
        })
    
    return render(request, 'monitoring/health.html', {
        'health_data': health_data
    })

def metrics(request):
    # Get filter parameters
    cluster_id = request.GET.get('cluster')
    metric_type = request.GET.get('type')
    time_range = request.GET.get('range', '24h')
    
    # Calculate time range
    now = timezone.now()
    if time_range == '1h':
        start_time = now - timedelta(hours=1)
    elif time_range == '7d':
        start_time = now - timedelta(days=7)
    elif time_range == '30d':
        start_time = now - timedelta(days=30)
    else:  # Default to 24h
        start_time = now - timedelta(hours=24)
    
    # Base queryset
    metrics = Metric.objects.filter(timestamp__gte=start_time)
    
    # Apply filters
    if cluster_id:
        metrics = metrics.filter(cluster_id=cluster_id)
    if metric_type:
        metrics = metrics.filter(type=metric_type)
    
    # Group metrics by name and calculate statistics
    grouped_metrics = {}
    for metric in metrics:
        if metric.name not in grouped_metrics:
            grouped_metrics[metric.name] = {
                'values': [],
                'timestamps': [],
                'current': 0,
                'average': 0,
                'peak': 0
            }
        
        data = grouped_metrics[metric.name]
        data['values'].append(float(metric.value))
        data['timestamps'].append(metric.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Update statistics
        data['current'] = metric.value
        data['peak'] = max(data['peak'], float(metric.value))
    
    # Calculate averages
    for name, data in grouped_metrics.items():
        if data['values']:
            data['average'] = sum(data['values']) / len(data['values'])
    
    context = {
        'clusters': Cluster.objects.all(),
        'selected_cluster': cluster_id,
        'selected_type': metric_type,
        'time_range': time_range,
        'grouped_metrics': grouped_metrics,
    }
    
    return render(request, 'monitoring/metrics.html', context)

def logs(request):
    cluster_id = request.GET.get('cluster')
    log_level = request.GET.get('level')
    search = request.GET.get('search')
    
    logs = Log.objects.all()
    
    if cluster_id:
        logs = logs.filter(cluster_id=cluster_id)
    if log_level:
        logs = logs.filter(level=log_level)
    if search:
        logs = logs.filter(message__icontains=search)
    
    logs = logs.order_by('-timestamp')
    
    return render(request, 'monitoring/logs.html', {
        'logs': logs,
        'clusters': Cluster.objects.all(),
        'selected_cluster': cluster_id,
        'selected_level': log_level,
        'search_query': search
    })

def alerts(request):
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    cluster_id = request.GET.get('cluster')
    
    alerts = Alert.objects.all()
    
    if severity:
        alerts = alerts.filter(severity=severity)
    if status == 'active':
        alerts = alerts.filter(is_resolved=False)
    elif status == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    if cluster_id:
        alerts = alerts.filter(cluster_id=cluster_id)
    
    alerts = alerts.order_by('-created_at')
    
    return render(request, 'monitoring/alerts.html', {
        'alerts': alerts,
        'clusters': Cluster.objects.all(),
        'selected_severity': severity,
        'selected_status': status,
        'selected_cluster': cluster_id
    })

@login_required
@require_POST
def acknowledge_alert(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    alert.acknowledge(request.user)
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def resolve_alert(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    alert.resolve()
    return JsonResponse({'status': 'success'})
