from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ClusterHealth, Alert, Metric, Log
from clusters.models import Cluster
from dags.models import DAG, TaskInstance
import psutil
import json

channel_layer = get_channel_layer()

@shared_task
def collect_system_metrics():
    """Collect system-wide metrics"""
    for cluster in Cluster.objects.all():
        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Create system metrics
        metrics = [
            Metric(
                cluster=cluster,
                name='cpu_usage',
                type='system',
                value=cpu_usage,
                unit='%',
                threshold_warning=75,
                threshold_critical=90
            ),
            Metric(
                cluster=cluster,
                name='memory_usage',
                type='system',
                value=memory.percent,
                unit='%',
                threshold_warning=75,
                threshold_critical=90
            ),
            Metric(
                cluster=cluster,
                name='disk_usage',
                type='system',
                value=disk.percent,
                unit='%',
                threshold_warning=75,
                threshold_critical=90
            )
        ]
        Metric.objects.bulk_create(metrics)

        # Check thresholds and create alerts
        for metric in metrics:
            metric.check_thresholds()

@shared_task
def collect_airflow_metrics():
    """Collect Airflow-specific metrics"""
    now = timezone.now()
    last_day = now - timedelta(days=1)

    for cluster in Cluster.objects.all():
        # Get DAG-specific metrics
        for dag in DAG.objects.filter(cluster=cluster):
            # Task success rate
            task_stats = TaskInstance.objects.filter(
                dag=dag,
                end_date__gte=last_day
            ).aggregate(
                total=Count('id'),
                success=Count('id', filter=models.Q(status='success')),
                failed=Count('id', filter=models.Q(status='failed')),
                running=Count('id', filter=models.Q(status='running'))
            )

            success_rate = (task_stats['success'] / task_stats['total'] * 100) if task_stats['total'] > 0 else 0

            # Average task duration
            avg_duration = TaskInstance.objects.filter(
                dag=dag,
                end_date__gte=last_day,
                duration__isnull=False
            ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0

            # Create metrics
            metrics = [
                Metric(
                    cluster=cluster,
                    name='task_success_rate',
                    type='airflow',
                    value=success_rate,
                    unit='%',
                    threshold_warning=90,
                    threshold_critical=80,
                    metadata={'dag_id': dag.dag_id}
                ),
                Metric(
                    cluster=cluster,
                    name='avg_task_duration',
                    type='airflow',
                    value=avg_duration,
                    unit='s',
                    metadata={'dag_id': dag.dag_id}
                ),
                Metric(
                    cluster=cluster,
                    name='running_tasks',
                    type='airflow',
                    value=task_stats['running'],
                    metadata={'dag_id': dag.dag_id}
                )
            ]
            Metric.objects.bulk_create(metrics)

            # Resource usage metrics
            try:
                dag_processes = [p for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])
                               if dag.dag_id in p.info['name']]
                
                if dag_processes:
                    total_cpu = sum(p.info['cpu_percent'] for p in dag_processes)
                    total_memory = sum(p.info['memory_percent'] for p in dag_processes)

                    resource_metrics = [
                        Metric(
                            cluster=cluster,
                            name='cpu_usage',
                            type='airflow',
                            value=total_cpu,
                            unit='%',
                            metadata={'dag_id': dag.dag_id}
                        ),
                        Metric(
                            cluster=cluster,
                            name='memory_usage',
                            type='airflow',
                            value=total_memory,
                            unit='%',
                            metadata={'dag_id': dag.dag_id}
                        )
                    ]
                    Metric.objects.bulk_create(resource_metrics)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass

@shared_task
def update_cluster_health():
    """Update cluster health status"""
    for cluster in Cluster.objects.all():
        # Get latest metrics
        latest_metrics = {
            m.name: m.value for m in Metric.objects.filter(
                cluster=cluster,
                type='system',
                timestamp__gte=timezone.now() - timedelta(minutes=5)
            )
        }

        # Count failed tasks in last 24h
        failed_tasks = TaskInstance.objects.filter(
            dag__cluster=cluster,
            end_date__gte=timezone.now() - timedelta(hours=24),
            status='failed'
        ).count()

        # Get scheduler heartbeat
        try:
            scheduler_process = next(p for p in psutil.process_iter(['name'])
                                  if 'airflow-scheduler' in p.info['name'])
            scheduler_heartbeat = timezone.now()
        except StopIteration:
            scheduler_heartbeat = timezone.now() - timedelta(minutes=10)

        # Calculate average DAG processing time
        dag_processing_times = Metric.objects.filter(
            cluster=cluster,
            name='avg_task_duration',
            type='airflow',
            timestamp__gte=timezone.now() - timedelta(hours=1)
        ).values_list('value', flat=True)
        
        avg_processing_time = sum(dag_processing_times) / len(dag_processing_times) if dag_processing_times else 0

        # Update or create health check
        health_check, _ = ClusterHealth.objects.update_or_create(
            cluster=cluster,
            defaults={
                'cpu_usage': latest_metrics.get('cpu_usage', 0),
                'memory_usage': latest_metrics.get('memory_usage', 0),
                'disk_usage': latest_metrics.get('disk_usage', 0),
                'scheduler_heartbeat': scheduler_heartbeat,
                'dag_processing_time': avg_processing_time,
                'active_dag_runs': DAG.objects.filter(cluster=cluster, is_active=True).count(),
                'queued_tasks': TaskInstance.objects.filter(
                    dag__cluster=cluster,
                    status='queued'
                ).count(),
                'running_tasks': TaskInstance.objects.filter(
                    dag__cluster=cluster,
                    status='running'
                ).count(),
                'failed_tasks_24h': failed_tasks
            }
        )
        
        # Update status based on metrics
        health_check.update_status()

@shared_task
def broadcast_monitoring_data():
    """Broadcast monitoring data to all connected clients"""
    consumer = MonitoringConsumer()
    data = consumer.get_monitoring_data()
    
    async_to_sync(channel_layer.group_send)(
        "monitoring",
        {
            "type": "monitoring_update",
            "data": data
        }
    )

@shared_task
def create_alert(cluster, title, message, severity='warning'):
    """Create a new alert."""
    try:
        Alert.objects.create(
            cluster_id=cluster,
            title=title,
            message=message,
            severity=severity
        )
    except Exception as e:
        logger.error(f"Error creating alert: {str(e)}")
        Log.objects.create(
            level='error',
            message=f"Failed to create alert: {str(e)}",
            source='monitoring.tasks.create_alert'
        )

@shared_task
def cleanup_old_metrics():
    """Clean up old metrics, logs, and resolved alerts."""
    try:
        cutoff_metrics = timezone.now() - timedelta(
            days=settings.MONITORING['METRIC_RETENTION_DAYS']
        )
        cutoff_alerts = timezone.now() - timedelta(
            days=settings.MONITORING['ALERT_RETENTION_DAYS']
        )
        cutoff_logs = timezone.now() - timedelta(
            days=settings.MONITORING['LOG_RETENTION_DAYS']
        )
        
        # Delete old data
        Metric.objects.filter(timestamp__lt=cutoff_metrics).delete()
        Alert.objects.filter(
            resolved_at__lt=cutoff_alerts,
            status='resolved'
        ).delete()
        Log.objects.filter(timestamp__lt=cutoff_logs).delete()
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
        Log.objects.create(
            level='error',
            message=f"Failed to clean up old data: {str(e)}",
            source='monitoring.tasks.cleanup_old_metrics'
        )
