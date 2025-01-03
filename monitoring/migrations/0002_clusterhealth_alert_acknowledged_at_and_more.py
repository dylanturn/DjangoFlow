# Generated by Django 4.2.16 on 2024-12-04 17:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clusters", "0002_remove_cluster_api_key_cluster_password_and_more"),
        ("monitoring", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClusterHealth",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("healthy", "Healthy"),
                            ("warning", "Warning"),
                            ("critical", "Critical"),
                            ("unknown", "Unknown"),
                        ],
                        default="unknown",
                        max_length=20,
                    ),
                ),
                ("cpu_usage", models.FloatField(help_text="CPU usage in percentage")),
                (
                    "memory_usage",
                    models.FloatField(help_text="Memory usage in percentage"),
                ),
                ("disk_usage", models.FloatField(help_text="Disk usage in percentage")),
                (
                    "scheduler_heartbeat",
                    models.DateTimeField(help_text="Last scheduler heartbeat"),
                ),
                (
                    "dag_processing_time",
                    models.FloatField(
                        help_text="Average DAG processing time in seconds"
                    ),
                ),
                (
                    "active_dag_runs",
                    models.IntegerField(help_text="Number of active DAG runs"),
                ),
                (
                    "queued_tasks",
                    models.IntegerField(help_text="Number of queued tasks"),
                ),
                (
                    "running_tasks",
                    models.IntegerField(help_text="Number of running tasks"),
                ),
                (
                    "failed_tasks_24h",
                    models.IntegerField(
                        help_text="Number of failed tasks in last 24 hours"
                    ),
                ),
                ("last_checked", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-last_checked"],
                "get_latest_by": "last_checked",
            },
        ),
        migrations.AddField(
            model_name="alert",
            name="acknowledged_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="alert",
            name="acknowledged_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="acknowledged_alerts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="log",
            name="metadata",
            field=models.JSONField(
                blank=True, default=dict, help_text="Additional log metadata"
            ),
        ),
        migrations.AddField(
            model_name="log",
            name="source",
            field=models.CharField(
                default="system",
                help_text="Log source (e.g., scheduler, webserver, worker)",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="metric",
            name="threshold_critical",
            field=models.FloatField(
                blank=True, help_text="Critical threshold value", null=True
            ),
        ),
        migrations.AddField(
            model_name="metric",
            name="threshold_warning",
            field=models.FloatField(
                blank=True, help_text="Warning threshold value", null=True
            ),
        ),
        migrations.AddField(
            model_name="metric",
            name="type",
            field=models.CharField(
                choices=[
                    ("system", "System Metric"),
                    ("airflow", "Airflow Metric"),
                    ("custom", "Custom Metric"),
                ],
                default="system",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="log",
            index=models.Index(
                fields=["level", "-timestamp"], name="monitoring__level_a512c9_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="log",
            index=models.Index(
                fields=["source", "-timestamp"], name="monitoring__source_7fe028_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="metric",
            index=models.Index(
                fields=["type", "-timestamp"], name="monitoring__type_82038c_idx"
            ),
        ),
        migrations.AddField(
            model_name="clusterhealth",
            name="cluster",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="monitoring_health_checks",
                to="clusters.cluster",
            ),
        ),
    ]
