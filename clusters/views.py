from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Cluster
from .forms import ClusterForm
from .services import AirflowAPIService
from dags.models import DAG

# Create your views here.

def cluster_list(request):
    clusters = Cluster.objects.all()
    return render(request, 'clusters/list.html', {'clusters': clusters})

def cluster_detail(request, pk):
    cluster = get_object_or_404(Cluster, pk=pk)
    airflow_service = AirflowAPIService(cluster)
    
    # Sync DAGs from Airflow
    airflow_service.sync_dags()
    
    # Get DAGs from local database
    dags = DAG.objects.filter(cluster=cluster, is_active=True)
    
    context = {
        'cluster': cluster,
        'dags': dags,
    }
    return render(request, 'clusters/detail.html', context)

def cluster_add(request):
    if request.method == 'POST':
        form = ClusterForm(request.POST)
        if form.is_valid():
            cluster = form.save()
            messages.success(request, f'Cluster {cluster.name} created successfully.')
            return redirect('cluster_detail', pk=cluster.pk)
    else:
        form = ClusterForm()
    return render(request, 'clusters/form.html', {'form': form, 'title': 'Create Cluster'})

def cluster_edit(request, pk):
    cluster = get_object_or_404(Cluster, pk=pk)
    if request.method == 'POST':
        form = ClusterForm(request.POST, instance=cluster)
        if form.is_valid():
            cluster = form.save()
            messages.success(request, f'Cluster {cluster.name} updated successfully.')
            return redirect('cluster_detail', pk=cluster.pk)
    else:
        form = ClusterForm(instance=cluster)
    return render(request, 'clusters/form.html', {'form': form, 'title': 'Update Cluster'})

@require_POST
def cluster_delete(request, pk):
    cluster = get_object_or_404(Cluster, pk=pk)
    name = cluster.name
    cluster.delete()
    messages.success(request, f'Cluster {name} deleted successfully.')
    return redirect('cluster_list')

@require_POST
def refresh_health(request, pk):
    cluster = get_object_or_404(Cluster, pk=pk)
    airflow_service = AirflowAPIService(cluster)
    health_check = airflow_service.check_health()
    
    return JsonResponse({
        'status': health_check.status,
        'scheduler_status': health_check.scheduler_status,
        'dag_processor_status': health_check.dag_processor_status,
        'metadata_db_status': health_check.metadata_db_status,
        'last_check': health_check.created_at.isoformat(),
    })

@require_POST
def refresh_dags(request, pk):
    cluster = get_object_or_404(Cluster, pk=pk)
    airflow_service = AirflowAPIService(cluster)
    synced_dags = airflow_service.sync_dags()
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully synced {len(synced_dags)} DAGs',
    })
