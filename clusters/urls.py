from django.urls import path
from . import views

app_name = 'clusters'

urlpatterns = [
    path('', views.cluster_list, name='list'),
    path('add/', views.cluster_add, name='cluster_add'),
    path('<int:pk>/', views.cluster_detail, name='cluster_detail'),
    path('<int:pk>/edit/', views.cluster_edit, name='cluster_edit'),
    path('<int:pk>/delete/', views.cluster_delete, name='cluster_delete'),
    path('<int:pk>/refresh-health/', views.refresh_health, name='refresh_health'),
    path('<int:pk>/refresh-dags/', views.refresh_dags, name='refresh_dags'),
]
