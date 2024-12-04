from django.urls import path
from . import views

app_name = 'dags'

urlpatterns = [
    path('', views.dag_list, name='list'),
    path('<str:dag_id>/', views.dag_details, name='detail'),
    path('<str:dag_id>/runs/', views.dag_runs, name='runs'),
    path('<str:dag_id>/logs/', views.dag_logs, name='logs'),
    path('<str:dag_id>/toggle_pause/', views.toggle_pause, name='toggle_pause'),
    path('<str:dag_id>/trigger/', views.trigger_dag, name='trigger'),
    path('<str:dag_id>/edit/', views.dag_edit, name='edit'),
    path('<str:dag_id>/delete/', views.dag_delete, name='delete'),
]
