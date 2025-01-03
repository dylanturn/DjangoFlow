# Generated by Django 4.2.16 on 2024-12-04 04:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("dags", "0001_initial"),
        ("clusters", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Alert",
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
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("critical", "Critical"),
                            ("warning", "Warning"),
                            ("info", "Info"),
                        ],
                        max_length=20,
                    ),
                ),
                ("is_resolved", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="clusters.cluster",
                    ),
                ),
                (
                    "dag",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="dags.dag",
                    ),
                ),
                (
                    "task_instance",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alerts",
                        to="dags.taskinstance",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Metric",
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
                ("name", models.CharField(max_length=100)),
                ("value", models.FloatField()),
                ("unit", models.CharField(blank=True, max_length=50)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="metrics",
                        to="clusters.cluster",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["cluster", "name", "-timestamp"],
                        name="monitoring__cluster_40e08c_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Log",
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
                    "level",
                    models.CharField(
                        choices=[
                            ("debug", "Debug"),
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("critical", "Critical"),
                        ],
                        max_length=20,
                    ),
                ),
                ("message", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs",
                        to="clusters.cluster",
                    ),
                ),
                (
                    "dag",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs",
                        to="dags.dag",
                    ),
                ),
                (
                    "task_instance",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="logs",
                        to="dags.taskinstance",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["cluster", "-timestamp"],
                        name="monitoring__cluster_bd30ac_idx",
                    ),
                    models.Index(
                        fields=["dag", "-timestamp"],
                        name="monitoring__dag_id_aeb991_idx",
                    ),
                    models.Index(
                        fields=["task_instance", "-timestamp"],
                        name="monitoring__task_in_4d6c2a_idx",
                    ),
                ],
            },
        ),
    ]
