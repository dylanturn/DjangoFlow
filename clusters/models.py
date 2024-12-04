from django.db import models
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta


class Cluster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    endpoint = models.URLField(help_text="Airflow API endpoint URL")
    username = models.CharField(max_length=100, help_text="Username for Airflow basic auth", default='admin')
    password = models.CharField(max_length=100, help_text="Password for Airflow basic auth", default='admin')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('clusters:detail', kwargs={'pk': self.pk})

    def get_latest_health(self):
        """Get the most recent health check."""
        return self.health_checks.first()

    def get_health(self):
        """Get the current health status with a 5-minute cache."""
        latest = self.get_latest_health()
        if latest and latest.checked_at > timezone.now() - timedelta(minutes=5):
            return latest
        return self.update_health()

    def update_health(self):
        """Perform a new health check."""
        from .services import AirflowAPIService
        service = AirflowAPIService(self)
        return service.check_health()


class ClusterHealth(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='health_checks')
    status = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('unhealthy', 'Unhealthy'),
        ('unknown', 'Unknown')
    ])
    scheduler_status = models.CharField(max_length=20)
    dag_processor_status = models.CharField(max_length=20)
    metadata_db_status = models.CharField(max_length=20)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-checked_at']
        get_latest_by = 'checked_at'

    def __str__(self):
        return f"{self.cluster.name} - {self.status} at {self.checked_at}"

    @property
    def is_healthy(self):
        """Check if the cluster is healthy."""
        return self.status == 'healthy'

    @property
    def details(self):
        """Get component health details."""
        return {
            'scheduler': self.scheduler_status == 'healthy',
            'dag_processor': self.dag_processor_status == 'healthy',
            'metadatabase': self.metadata_db_status == 'healthy'
        }
