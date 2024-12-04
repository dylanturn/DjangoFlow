from django.db import models
from clusters.models import Cluster


class DAG(models.Model):
    cluster = models.ForeignKey(Cluster, on_delete=models.CASCADE, related_name='dags')
    dag_id = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    is_paused = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    file_location = models.CharField(max_length=500)
    last_parsed = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cluster', 'dag_id')
        ordering = ['dag_id']

    def __str__(self):
        return f"{self.dag_id} ({self.cluster.name})"


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
