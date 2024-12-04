from django.db.models import Count, Avg, F, ExpressionWrapper, FloatField, Q, StdDev
from django.utils import timezone
from datetime import timedelta
from .models import TaskInstance, DAGRun, DAG

class TaskStatistics:
    def __init__(self, dag=None, time_range=None):
        self.dag = dag
        self.time_range = time_range or timedelta(days=7)
        self.base_queryset = TaskInstance.objects.all()
        if dag:
            self.base_queryset = self.base_queryset.filter(dag_run__dag=dag)

    def get_performance_metrics(self):
        """Calculate performance metrics for tasks"""
        cutoff_date = timezone.now() - self.time_range
        return self.base_queryset.filter(
            start_date__gte=cutoff_date
        ).values('task_id').annotate(
            total_runs=Count('id'),
            avg_duration=Avg('duration'),
            std_duration=StdDev('duration'),
            success_rate=ExpressionWrapper(
                Count('id', filter=Q(state='success')) * 100.0 / Count('id'),
                output_field=FloatField()
            ),
            failure_rate=ExpressionWrapper(
                Count('id', filter=Q(state='failed')) * 100.0 / Count('id'),
                output_field=FloatField()
            ),
            retry_rate=ExpressionWrapper(
                Avg('try_number', output_field=FloatField()) - 1.0,
                output_field=FloatField()
            )
        )

    def get_scheduler_health(self):
        """Analyze scheduler health metrics"""
        cutoff_date = timezone.now() - self.time_range
        return {
            'scheduled_tasks': self.base_queryset.filter(
                start_date__gte=cutoff_date
            ).count(),
            'execution_delays': self.base_queryset.filter(
                start_date__gte=cutoff_date
            ).exclude(
                state__in=['success', 'failed']
            ).count(),
            'queued_tasks': self.base_queryset.filter(
                state='queued'
            ).count(),
            'running_tasks': self.base_queryset.filter(
                state='running'
            ).count()
        }

    def get_task_trends(self):
        """Analyze task execution trends over time"""
        cutoff_date = timezone.now() - self.time_range
        return self.base_queryset.filter(
            start_date__gte=cutoff_date
        ).values('dag_run__execution_date__date').annotate(
            total_tasks=Count('id'),
            successful_tasks=Count('id', filter=Q(state='success')),
            failed_tasks=Count('id', filter=Q(state='failed')),
            avg_duration=Avg('duration')
        ).order_by('dag_run__execution_date__date')

    def get_task_dependencies(self):
        """Analyze task dependencies and their impact on performance"""
        return self.base_queryset.values(
            'task_id',
            'dag_run__dag__dag_id'
        ).annotate(
            upstream_delay=Avg('start_date', filter=Q(state='upstream_failed')),
            downstream_impact=Count('id', filter=Q(state='skipped'))
        )

    def get_resource_utilization(self):
        """Analyze resource utilization patterns"""
        cutoff_date = timezone.now() - self.time_range
        return self.base_queryset.filter(
            start_date__gte=cutoff_date,
            state='success'
        ).values('task_id').annotate(
            avg_duration=Avg('duration'),
            peak_duration=Max('duration'),
            total_execution_time=Sum('duration'),
            concurrent_executions=Count('id', filter=Q(state='running'))
        )

    def get_task_summary(self):
        """Get a comprehensive summary of task statistics"""
        metrics = self.get_performance_metrics()
        scheduler_health = self.get_scheduler_health()
        trends = self.get_task_trends()
        
        return {
            'performance_metrics': metrics,
            'scheduler_health': scheduler_health,
            'execution_trends': trends,
            'last_updated': timezone.now()
        }
