import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoflow.settings')

app = Celery('djangoflow')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'collect-system-metrics': {
        'task': 'monitoring.tasks.collect_system_metrics',
        'schedule': 60.0,  # Every minute
    },
    'collect-airflow-metrics': {
        'task': 'monitoring.tasks.collect_airflow_metrics',
        'schedule': 300.0,  # Every 5 minutes
    },
    'check-cluster-health': {
        'task': 'monitoring.tasks.check_cluster_health',
        'schedule': 60.0,  # Every minute
    },
    'cleanup-old-metrics': {
        'task': 'monitoring.tasks.cleanup_old_metrics',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}
