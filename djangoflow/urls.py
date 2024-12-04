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
    context = {
        'active_dags': DAG.objects.filter(is_active=True).count(),
        'active_clusters': Cluster.objects.filter(is_active=True).count(),
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
