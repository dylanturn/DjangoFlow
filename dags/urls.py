from django.urls import path
from . import views

app_name = 'dags'

urlpatterns = [
    path('', views.dag_list, name='list'),
    path('<int:id>/', views.dag_details, name='details'),
    path('<int:id>/edit/', views.dag_edit, name='edit'),
    path('<int:id>/delete/', views.dag_delete, name='delete'),
    path('<int:id>/runs/', views.dag_runs, name='runs'),
    path('<int:id>/runs/<str:run_id>/', views.run_detail, name='run_detail'),
    path('<int:id>/logs/', views.dag_logs, name='logs'),
    path('<int:id>/tasks/', views.dag_tasks, name='tasks'),
    path('<int:id>/toggle_pause/', views.toggle_pause, name='toggle_pause'),
    path('<int:id>/trigger/', views.trigger_dag, name='trigger'),
    path('api/dag-schedules/', views.get_dag_schedules, name='dag_schedules'),
]
