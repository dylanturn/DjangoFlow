import os
import sys
import django
import logging
import traceback

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoflow.settings')

# Configure Django
django.setup()

# Import required models and tasks
from clusters.models import Cluster
from dags.models import DAG, DAGRun, TaskInstance
from dags.tasks import sync_dag_runs
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(project_root, 'logs', 'celery_debug.log'))
    ]
)
logger = logging.getLogger(__name__)

def debug_airflow_connection(cluster):
    """
    Comprehensive debugging of Airflow API connection
    """
    logger.info(f"\n🔍 Debugging Cluster: {cluster.name}")
    logger.info(f"Endpoint: {cluster.endpoint}")
    
    try:
        # Construct base URL
        base_url = f"{cluster.endpoint.rstrip('/')}/api/v1"
        
        # Test health endpoint
        health_url = f"{base_url}/health"
        logger.info(f"Checking health endpoint: {health_url}")
        
        response = requests.get(
            health_url, 
            auth=(cluster.username, cluster.password),
            timeout=10
        )
        
        logger.info(f"Health Check Status Code: {response.status_code}")
        logger.info(f"Health Check Response Headers: {response.headers}")
        
        # Try to parse response
        try:
            health_data = response.json()
            logger.info("Health Check Response JSON:")
            for key, value in health_data.items():
                logger.info(f"  {key}: {value}")
        except ValueError:
            logger.warning("Could not parse health check response as JSON")
            logger.warning(f"Response Text: {response.text}")
        
        # Test DAGs endpoint
        dags_url = f"{base_url}/dags"
        logger.info(f"\nFetching DAGs from: {dags_url}")
        
        dags_response = requests.get(
            dags_url,
            auth=(cluster.username, cluster.password),
            timeout=10
        )
        
        logger.info(f"DAGs Endpoint Status Code: {dags_response.status_code}")
        
        try:
            dags_data = dags_response.json()
            logger.info(f"Total DAGs found: {len(dags_data.get('dags', []))}")
            
            # Print first few DAG details
            for dag in dags_data.get('dags', [])[:5]:
                logger.info(f"  DAG ID: {dag.get('dag_id')}")
        except ValueError:
            logger.warning("Could not parse DAGs response as JSON")
            logger.warning(f"Response Text: {dags_response.text}")
    
    except requests.RequestException as e:
        logger.error(f"Connection Error: {e}")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Unexpected Error: {e}")
        logger.error(traceback.format_exc())

def main():
    """
    Main debugging script
    """
    logger.info("🚀 Starting Airflow API Debugging Script")
    
    # Fetch and debug all clusters
    clusters = Cluster.objects.all()
    logger.info(f"Found {clusters.count()} clusters")
    
    for cluster in clusters:
        debug_airflow_connection(cluster)
    
    # Fetch local DAGs
    logger.info("\n📊 Local DAG Information")
    dags = DAG.objects.all()
    for dag in dags:
        logger.info(f"DAG: {dag.dag_id} (Cluster: {dag.cluster.name})")
        run_count = DAGRun.objects.filter(dag=dag).count()
        logger.info(f"  Existing DAG Runs: {run_count}")
    
    # Manually trigger sync
    logger.info("\n🔄 Triggering DAG Runs Synchronization")
    try:
        sync_result = sync_dag_runs()
        logger.info("Sync Result:")
        for key, value in sync_result.items():
            logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"Sync Task Failed: {e}")
        logger.error(traceback.format_exc())
    
    # Check DAG runs after sync
    logger.info("\n📈 DAG Runs After Sync")
    for dag in dags:
        run_count = DAGRun.objects.filter(dag=dag).count()
        logger.info(f"DAG: {dag.dag_id} - Runs: {run_count}")

if __name__ == '__main__':
    main()