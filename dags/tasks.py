import logging
import traceback
import requests
from celery import shared_task
from django.utils import timezone
from datetime import datetime
from .models import DAG, DAGRun, TaskInstance
from clusters.models import Cluster

logger = logging.getLogger(__name__)

def debug_log_request(method, url, auth, headers=None):
    """
    Log details of an HTTP request for debugging purposes.
    """
    logger.debug(f"Making {method} request to: {url}")
    logger.debug(f"Authentication: {'Provided' if auth else 'Not provided'}")
    if headers:
        logger.debug(f"Headers: {headers}")
    
    try:
        response = requests.request(method, url, auth=auth, headers=headers, timeout=10)
        logger.debug(f"Response Status Code: {response.status_code}")
        logger.debug(f"Response Headers: {response.headers}")
        
        # Try to parse and log JSON response
        try:
            json_response = response.json()
            logger.debug(f"Response JSON (first 500 chars): {str(json_response)[:500]}")
        except ValueError:
            logger.debug(f"Response Text (first 500 chars): {response.text[:500]}")
        
        return response
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        logger.error(traceback.format_exc())
        return None

@shared_task(bind=True)
def sync_dag_runs(self):
    """
    Comprehensive DAG runs synchronization with extensive logging and error handling.
    Ensures that a single cluster connection failure does not prevent synchronization of other clusters.
    """
    logger.info("🚀 Starting DAG Runs Synchronization")
    
    # Track overall sync performance
    total_clusters = 0
    total_dags = 0
    total_dag_runs = 0
    total_task_instances = 0
    sync_errors = []
    
    try:
        # Fetch all active clusters
        clusters = Cluster.objects.filter(is_active=True)
        total_clusters = clusters.count()
        logger.info(f"Found {total_clusters} active clusters to process")
        
        for cluster in clusters:
            try:
                logger.info(f"\n🌐 Processing Cluster: {cluster.name} (ID: {cluster.id})")
                
                # Validate cluster configuration
                if not all([cluster.endpoint, cluster.username, cluster.password]):
                    raise ValueError(f"Incomplete cluster configuration: {cluster.name}")
                
                # Prepare API base URL and authentication
                base_url = f"{cluster.endpoint.rstrip('/')}/api/v1"
                auth = (cluster.username, cluster.password)
                
                # Fetch DAGs for this cluster
                cluster_dags = DAG.objects.filter(cluster=cluster)
                total_dags += cluster_dags.count()
                logger.info(f"Found {cluster_dags.count()} DAGs for cluster {cluster.name}")
                
                for dag in cluster_dags:
                    logger.info(f"\n📊 Processing DAG: {dag.dag_id}")
                    
                    try:
                        # Fetch DAG runs from Airflow API
                        dag_runs_url = f"{base_url}/dags/{dag.dag_id}/dagRuns"
                        dag_runs_response = debug_log_request('GET', dag_runs_url, auth, 
                                                              headers={'Content-Type': 'application/json'})
                        
                        if not dag_runs_response or dag_runs_response.status_code != 200:
                            error_msg = f"Failed to fetch DAG runs for {dag.dag_id}"
                            logger.error(error_msg)
                            sync_errors.append(error_msg)
                            continue
                        
                        dag_runs_data = dag_runs_response.json()
                        dag_runs = dag_runs_data.get('dag_runs', [])
                        
                        logger.info(f"Found {len(dag_runs)} DAG runs")
                        total_dag_runs += len(dag_runs)
                        
                        for run_data in dag_runs:
                            # Create or update DAG run
                            try:
                                dag_run, created = DAGRun.objects.update_or_create(
                                    dag=dag,
                                    run_id=run_data.get('run_id', ''),
                                    defaults={
                                        'state': run_data.get('state', 'unknown'),
                                        'execution_date': datetime.fromisoformat(run_data.get('execution_date', '').replace('Z', '+00:00')) if run_data.get('execution_date') else None,
                                        'start_date': datetime.fromisoformat(run_data.get('start_date', '').replace('Z', '+00:00')) if run_data.get('start_date') else None,
                                        'end_date': datetime.fromisoformat(run_data.get('end_date', '').replace('Z', '+00:00')) if run_data.get('end_date') else None,
                                        'external_trigger': run_data.get('external_trigger', False)
                                    }
                                )
                                
                                logger.info(f"{'Created' if created else 'Updated'} DAG run: {dag_run}")
                                
                                # Fetch task instances for this DAG run
                                task_instances_url = f"{base_url}/dags/{dag.dag_id}/dagRuns/{run_data.get('run_id')}/taskInstances"
                                task_instances_response = debug_log_request('GET', task_instances_url, auth, 
                                                                            headers={'Content-Type': 'application/json'})
                                
                                if task_instances_response and task_instances_response.status_code == 200:
                                    tasks_data = task_instances_response.json()
                                    task_instances = tasks_data.get('task_instances', [])
                                    
                                    for task_instance in task_instances:
                                        _, created = TaskInstance.objects.update_or_create(
                                            dag_run=dag_run,
                                            task_id=task_instance.get('task_id', ''),
                                            try_number=task_instance.get('try_number', 1),
                                            defaults={
                                                'state': task_instance.get('state', 'unknown'),
                                                'start_date': datetime.fromisoformat(task_instance.get('start_date', '').replace('Z', '+00:00')) if task_instance.get('start_date') else None,
                                                'end_date': datetime.fromisoformat(task_instance.get('end_date', '').replace('Z', '+00:00')) if task_instance.get('end_date') else None,
                                                'duration': task_instance.get('duration')
                                            }
                                        )
                                    
                                    total_task_instances += len(task_instances)
                                    logger.info(f"Processed {len(task_instances)} task instances")
                            
                            except Exception as run_error:
                                error_msg = f"Error processing DAG run {run_data.get('run_id')}: {run_error}"
                                logger.error(error_msg)
                                sync_errors.append(error_msg)
                    
                    except Exception as dag_error:
                        error_msg = f"Error processing DAG {dag.dag_id}: {dag_error}"
                        logger.error(error_msg)
                        sync_errors.append(error_msg)
            
            except Exception as cluster_error:
                error_msg = f"Error processing cluster {cluster.name}: {cluster_error}"
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                sync_errors.append(error_msg)
                # Continue to next cluster even if this one fails completely
                continue
        
        # Log sync summary
        logger.info("\n📈 Synchronization Summary:")
        logger.info(f"Clusters processed: {total_clusters}")
        logger.info(f"DAGs processed: {total_dags}")
        logger.info(f"DAG runs synchronized: {total_dag_runs}")
        logger.info(f"Task instances synchronized: {total_task_instances}")
        
        if sync_errors:
            logger.warning(f"Encountered {len(sync_errors)} errors during sync")
            for error in sync_errors[:10]:  # Log first 10 errors
                logger.warning(error)
    
    except Exception as overall_error:
        logger.critical(f"Critical error during DAG runs sync: {overall_error}")
        logger.critical(traceback.format_exc())
    
    logger.info("🏁 DAG Runs Synchronization Complete")
    
    return {
        'clusters_processed': total_clusters,
        'dags_processed': total_dags,
        'dag_runs_synced': total_dag_runs,
        'task_instances_synced': total_task_instances,
        'sync_errors': sync_errors
    }
