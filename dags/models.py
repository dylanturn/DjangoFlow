from django.db import models
from clusters.models import Cluster
from croniter import croniter
from datetime import timedelta, datetime
import re

class DAG(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='dags')
    dag_id = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    is_paused = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    file_location = models.CharField(max_length=500)
    last_parsed = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    schedule_interval = models.CharField(max_length=100, null=True, blank=True, help_text="Cron expression or interval (e.g. '@daily', '@hourly', '*/10 * * * *', '30m')")

    class Meta:
        unique_together = ('cluster', 'dag_id')
        ordering = ['dag_id']

    def __str__(self):
        return f"{self.dag_id} ({self.cluster.name})"

    def get_next_run_time(self, base_date):
        """Calculate the next run time based on schedule_interval."""
        if not self.schedule_interval:
            return None

        # Handle predefined schedules
        predefined = {
            '@yearly': '0 0 1 1 *',
            '@annually': '0 0 1 1 *',
            '@monthly': '0 0 1 * *',
            '@weekly': '0 0 * * 0',
            '@daily': '0 0 * * *',
            '@hourly': '0 * * * *',
        }

        schedule = self.schedule_interval.strip()

        # Handle predefined schedules
        if schedule in predefined:
            schedule = predefined[schedule]
            return croniter(schedule, base_date).get_next(datetime)

        # Handle time delta expressions (e.g., '30m', '1h', '1d')
        time_delta_match = re.match(r'^(\d+)([mhd])$', schedule)
        if time_delta_match:
            value, unit = time_delta_match.groups()
            value = int(value)
            if unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            else:  # unit == 'd'
                delta = timedelta(days=value)
            
            # Find the next scheduled time based on the interval
            current_time = base_date
            while current_time <= base_date:
                current_time += delta
            return current_time

        # Handle cron expressions
        try:
            return croniter(schedule, base_date).get_next(datetime)
        except Exception:
            return None


class DAGRun(models.Model):
    dag = models.ForeignKey(DAG, on_delete=models.CASCADE, related_name='runs')
    run_id = models.CharField(max_length=250)
    state = models.CharField(max_length=50)
    execution_date = models.DateTimeField()
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    external_trigger = models.BooleanField(default=False)

    class Meta:
        unique_together = ('dag', 'run_id')
        ordering = ['-execution_date']

    def __str__(self):
        return f"{self.dag.dag_id} - {self.run_id}"


class TaskInstance(models.Model):
    dag_run = models.ForeignKey(DAGRun, on_delete=models.CASCADE, related_name='task_instances')
    task_id = models.CharField(max_length=250)
    state = models.CharField(max_length=50)
    start_date = models.DateTimeField(null=True)
    end_date = models.DateTimeField(null=True)
    duration = models.FloatField(null=True)
    try_number = models.IntegerField(default=1)

    class Meta:
        unique_together = ('dag_run', 'task_id', 'try_number')
        ordering = ['task_id', '-try_number']

    def __str__(self):
        return f"{self.dag_run.dag.dag_id} - {self.task_id} (try {self.try_number})"
