from django.db import models
from django.utils import timezone
from clusters.models import Cluster
from dags.models import DAG, TaskInstance


class ClusterHealth(models.Model):
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('unknown', 'Unknown'),
    ]

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='monitoring_health_checks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    cpu_usage = models.FloatField(help_text='CPU usage in percentage')
    memory_usage = models.FloatField(help_text='Memory usage in percentage')
    disk_usage = models.FloatField(help_text='Disk usage in percentage')
    scheduler_heartbeat = models.DateTimeField(help_text='Last scheduler heartbeat')
    dag_processing_time = models.FloatField(help_text='Average DAG processing time in seconds')
    active_dag_runs = models.IntegerField(help_text='Number of active DAG runs')
    queued_tasks = models.IntegerField(help_text='Number of queued tasks')
    running_tasks = models.IntegerField(help_text='Number of running tasks')
    failed_tasks_24h = models.IntegerField(help_text='Number of failed tasks in last 24 hours')
    last_checked = models.DateTimeField(auto_now=True)

    def update_status(self):
        """Update cluster health status based on metrics"""
        if (self.cpu_usage > 90 or 
            self.memory_usage > 90 or 
            self.disk_usage > 90 or 
            self.failed_tasks_24h > 100 or
            timezone.now() - self.scheduler_heartbeat > timezone.timedelta(minutes=5)):
            self.status = 'critical'
        elif (self.cpu_usage > 75 or 
              self.memory_usage > 75 or 
              self.disk_usage > 75 or 
              self.failed_tasks_24h > 50 or
              timezone.now() - self.scheduler_heartbeat > timezone.timedelta(minutes=2)):
            self.status = 'warning'
        else:
            self.status = 'healthy'
        self.save()

    class Meta:
        ordering = ['-last_checked']
        get_latest_by = 'last_checked'

    def __str__(self):
        return f"{self.cluster.name} - {self.status} ({self.last_checked})"


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ]

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='alerts')
    dag = models.ForeignKey(DAG, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    task_instance = models.ForeignKey(TaskInstance, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    def acknowledge(self, user):
        """Acknowledge an alert"""
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()

    def resolve(self):
        """Resolve an alert"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.severity}: {self.title}"


class Metric(models.Model):
    METRIC_TYPES = [
        ('system', 'System Metric'),
        ('airflow', 'Airflow Metric'),
        ('custom', 'Custom Metric'),
    ]

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='metrics')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=METRIC_TYPES, default='system')
    value = models.FloatField()
    unit = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    threshold_warning = models.FloatField(null=True, blank=True, help_text='Warning threshold value')
    threshold_critical = models.FloatField(null=True, blank=True, help_text='Critical threshold value')
    
    def check_thresholds(self):
        """Check if metric exceeds thresholds and create alerts if needed"""
        if self.threshold_critical and self.value >= self.threshold_critical:
            Alert.objects.create(
                cluster=self.cluster,
                title=f"Critical: {self.name} exceeded threshold",
                message=f"{self.name} value {self.value}{self.unit} exceeded critical threshold {self.threshold_critical}{self.unit}",
                severity='critical'
            )
        elif self.threshold_warning and self.value >= self.threshold_warning:
            Alert.objects.create(
                cluster=self.cluster,
                title=f"Warning: {self.name} exceeded threshold",
                message=f"{self.name} value {self.value}{self.unit} exceeded warning threshold {self.threshold_warning}{self.unit}",
                severity='warning'
            )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['cluster', 'name', '-timestamp']),
            models.Index(fields=['type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.cluster.name} - {self.name}: {self.value}{self.unit}"


class Log(models.Model):
    LOG_LEVELS = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='logs')
    dag = models.ForeignKey(DAG, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    task_instance = models.ForeignKey(TaskInstance, on_delete=models.CASCADE, related_name='logs', null=True, blank=True)
    
    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=100, default='system', help_text='Log source (e.g., scheduler, webserver, worker)')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional log metadata')

    def create_alert_if_needed(self):
        """Create an alert for error and critical logs"""
        if self.level in ['error', 'critical']:
            Alert.objects.create(
                cluster=self.cluster,
                dag=self.dag,
                task_instance=self.task_instance,
                title=f"{self.level.title()} in {self.source}",
                message=self.message,
                severity='critical' if self.level == 'critical' else 'warning'
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            self.create_alert_if_needed()

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['cluster', '-timestamp']),
            models.Index(fields=['dag', '-timestamp']),
            models.Index(fields=['task_instance', '-timestamp']),
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['source', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.level}: {self.message[:100]}..."
