from django.core.management.base import BaseCommand
from django.utils import timezone
from dags.models import DAG
from clusters.models import Cluster

class Command(BaseCommand):
    help = 'Creates sample DAGs for development'

    def handle(self, *args, **options):
        # Get or create a sample cluster
        cluster, created = Cluster.objects.get_or_create(
            name='Sample Cluster',
            defaults={
                'endpoint': 'http://localhost:8080',
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created sample cluster: {cluster.name}'))

        # Create sample DAGs
        sample_dags = [
            {
                'dag_id': 'etl_pipeline',
                'description': 'Extract, Transform, Load pipeline for data processing',
                'file_location': '/dags/etl_pipeline.py',
            },
            {
                'dag_id': 'data_validation',
                'description': 'Data validation and quality checks',
                'file_location': '/dags/data_validation.py',
            },
            {
                'dag_id': 'reporting',
                'description': 'Generate daily reports and analytics',
                'file_location': '/dags/reporting.py',
            },
        ]

        for dag_data in sample_dags:
            dag, created = DAG.objects.get_or_create(
                cluster=cluster,
                dag_id=dag_data['dag_id'],
                defaults={
                    'description': dag_data['description'],
                    'file_location': dag_data['file_location'],
                    'is_active': True,
                    'is_paused': False,
                    'last_parsed': timezone.now(),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created sample DAG: {dag.dag_id}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'DAG already exists: {dag.dag_id}'))
