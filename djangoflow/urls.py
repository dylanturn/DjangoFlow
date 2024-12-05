"""
URL configuration for djangoflow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import json
from dags.models import DAG
from clusters.models import Cluster
from rest_framework import routers
from monitoring.api import (
    ClusterHealthViewSet,
    MetricViewSet,
    AlertViewSet,
    LogViewSet
)

def home(request):
    # Get base date (today)
    base_date = timezone.now()
    start_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timezone.timedelta(days=1)

    # Get all active DAGs
    active_dags = DAG.objects.filter(is_active=True).select_related('cluster')
    
    # Get schedule data for the timeline
    schedules = []
    for dag in active_dags:
        if dag.schedule_interval:
            next_run_time = dag.get_next_run_time(base_date)
            if next_run_time and start_date <= next_run_time <= end_date:
                # Get the latest run status
                latest_run = dag.runs.order_by('-execution_date').first()
                status = latest_run.state if latest_run else 'scheduled'
                
                schedules.append({
                    'dag_id': dag.dag_id,
                    'start_time': next_run_time.isoformat(),
                    'schedule_interval': dag.schedule_interval,
                    'cluster': dag.cluster.name,
                    'status': status
                })

    context = {
        'active_dags': active_dags.count(),
        'active_clusters': Cluster.objects.filter(is_active=True).count(),
        'dag_schedules': json.dumps(schedules, cls=DjangoJSONEncoder)
    }
    return render(request, 'home.html', context)

# Create a router and register our viewsets with it
router = routers.DefaultRouter()
router.register(r'health', ClusterHealthViewSet)
router.register(r'metrics', MetricViewSet)
router.register(r'alerts', AlertViewSet)
router.register(r'logs', LogViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),
    path("", home, name='home'),
    path("clusters/", include("clusters.urls", namespace='clusters')),
    path("dags/", include("dags.urls", namespace='dags')),
    path("monitoring/", include("monitoring.urls", namespace='monitoring')),
]
