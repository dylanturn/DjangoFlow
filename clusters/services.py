import requests
import logging
from typing import Dict, List
from datetime import datetime
from django.utils import timezone
from .models import ClusterHealth
from dags.models import DAG

logger = logging.getLogger(__name__)

class AirflowAPIService:
    def __init__(self, cluster):
        self.cluster = cluster
        self.auth = (cluster.username, cluster.password)
        # Ensure endpoint doesn't end with a slash
        self.endpoint = cluster.endpoint.rstrip('/')

    def check_health(self):
        """Check the health of the Airflow cluster."""
        try:
            logger.info(f"Checking health for cluster {self.cluster.name} at {self.endpoint}")
            response = requests.get(
                f"{self.endpoint}/health",
                auth=self.auth,
                timeout=5
            )
            
            logger.info(f"Health check status code: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"Health check failed with status code: {response.status_code}")
                return self._create_health_check('unhealthy', 'unknown', 'unknown', 'unknown')

            health_data = response.json()
            logger.info(f"Raw health check response: {health_data}")
            
            # If we get a 200 response, consider the cluster healthy
            return self._create_health_check(
                'healthy',  # Overall status
                'healthy',  # Scheduler
                'healthy',  # DAG processor
                'healthy'   # Metadata DB
            )

        except requests.RequestException as e:
            logger.error(f"Health check failed with exception: {str(e)}")
            return self._create_health_check('unhealthy', 'unknown', 'unknown', 'unknown')

    def sync_dags(self) -> List[DAG]:
        """
        Sync DAGs from Airflow to local database.
        Returns a list of synced DAG objects.
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/v1/dags",
                auth=self.auth,
                timeout=5
            )
            response.raise_for_status()
            
            dags_data = response.json()
            dags = dags_data.get('dags', [])
            
            # Update or create DAGs
            synced_dags = []
            for dag_data in dags:
                dag, created = DAG.objects.update_or_create(
                    cluster=self.cluster,
                    dag_id=dag_data['dag_id'],
                    defaults={
                        'description': dag_data.get('description', ''),
                        'is_paused': dag_data.get('is_paused', False),
                        'is_active': True,
                        'file_location': dag_data.get('file_token', ''),
                        'last_parsed': timezone.now(),
                    }
                )
                synced_dags.append(dag)
            
            # Mark DAGs not in Airflow as inactive
            DAG.objects.filter(cluster=self.cluster).exclude(
                dag_id__in=[d['dag_id'] for d in dags]
            ).update(is_active=False)
            
            return synced_dags
            
        except requests.RequestException as e:
            logger.error(f"Failed to sync DAGs: {str(e)}")
            return []

    def get_dags(self) -> List[Dict]:
        """
        Get list of DAGs from the Airflow cluster.
        Returns a list of DAG information dictionaries.
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/v1/dags",
                auth=self.auth,
                timeout=5
            )
            response.raise_for_status()
            
            dags_data = response.json()
            return dags_data.get('dags', [])
            
        except requests.RequestException as e:
            logger.error(f"Failed to get DAGs: {str(e)}")
            return []

    def get_dag_details(self, dag_id: str) -> Dict:
        """
        Get detailed information about a specific DAG.
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/v1/dags/{dag_id}",
                auth=self.auth,
                timeout=5
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to get DAG details for {dag_id}: {str(e)}")
            return {}

    def _create_health_check(self, status, scheduler_status, dag_processor_status, metadata_db_status):
        """Create a health check record."""
        logger.info(f"Creating health check record for {self.cluster.name}: {status}")
        return ClusterHealth.objects.create(
            cluster=self.cluster,
            status=status,
            scheduler_status=scheduler_status,
            dag_processor_status=dag_processor_status,
            metadata_db_status=metadata_db_status
        )
