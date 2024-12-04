import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Count
from .models import ClusterHealth, Alert, Metric, Log
from dags.models import DAG, TaskInstance

class MonitoringConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.time_range = '1h'  # Default time range
        await self.channel_layer.group_add("monitoring", self.channel_name)
        await self.accept()
        
        # Send initial data
        await self.send_monitoring_data()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("monitoring", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'time_range':
            self.time_range = data.get('range', '1h')
            await self.send_monitoring_data()
        elif message_type == 'refresh':
            await self.send_monitoring_data()

    async def monitoring_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def send_monitoring_data(self):
        data = await self.get_monitoring_data()
        await self.send(text_data=json.dumps(data))

    def get_time_threshold(self):
        now = timezone.now()
        if self.time_range == '1h':
            return now - timedelta(hours=1)
        elif self.time_range == '6h':
            return now - timedelta(hours=6)
        elif self.time_range == '24h':
            return now - timedelta(hours=24)
        elif self.time_range == '7d':
            return now - timedelta(days=7)
        return now - timedelta(hours=1)  # Default to 1 hour

    @sync_to_async
    def get_monitoring_data(self):
        threshold = self.get_time_threshold()
        
        # Get cluster health data
        cluster_health = list(ClusterHealth.objects.filter(
            last_checked__gte=threshold
        ).values())

        # Get recent alerts
        recent_alerts = list(Alert.objects.filter(
            is_resolved=False
        ).order_by('-created_at')[:10].values())

        # Get system metrics
        system_metrics = list(Metric.objects.filter(
            timestamp__gte=threshold,
            type='system'
        ).order_by('-timestamp').values())

        # Get DAG metrics
        dag_metrics = []
        for dag in DAG.objects.all():
            success_rate = TaskInstance.objects.filter(
                dag=dag,
                end_date__gte=threshold
            ).aggregate(
                success_rate=Count('status', filter=models.Q(status='success')) * 100.0 / Count('status')
            )['success_rate'] or 0
            
            dag_metrics.append({
                'dag_id': dag.dag_id,
                'success_rate': success_rate
            })

        # Get task duration metrics
        task_metrics = []
        for task in TaskInstance.objects.filter(
            end_date__gte=threshold
        ).values('task_id').distinct():
            durations = TaskInstance.objects.filter(
                task_id=task['task_id'],
                end_date__gte=threshold
            ).exclude(
                duration__isnull=True
            ).values_list('duration', 'end_date')
            
            if durations:
                task_metrics.append({
                    'task_id': task['task_id'],
                    'durations': list(durations)
                })

        # Get scheduler metrics
        scheduler_metrics = list(ClusterHealth.objects.filter(
            last_checked__gte=threshold
        ).values('scheduler_heartbeat', 'dag_processing_time', 'last_checked'))

        # Get resource usage by DAG
        resource_usage = []
        for dag in DAG.objects.all():
            avg_metrics = Metric.objects.filter(
                timestamp__gte=threshold,
                type='airflow',
                cluster=dag.cluster,
                metadata__dag_id=dag.dag_id
            ).aggregate(
                avg_cpu=Avg('value', filter=models.Q(name='cpu_usage')),
                avg_memory=Avg('value', filter=models.Q(name='memory_usage'))
            )
            
            resource_usage.append({
                'dag_id': dag.dag_id,
                'cpu_usage': avg_metrics['avg_cpu'] or 0,
                'memory_usage': avg_metrics['avg_memory'] or 0
            })

        return {
            'cluster_health': cluster_health,
            'recent_alerts': recent_alerts,
            'system_metrics': system_metrics,
            'dag_metrics': dag_metrics,
            'task_metrics': task_metrics,
            'scheduler_metrics': scheduler_metrics,
            'resource_usage': resource_usage
        }
