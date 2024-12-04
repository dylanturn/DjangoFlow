from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('health/', views.health_check, name='health'),
    path('metrics/', views.metrics, name='metrics'),
    path('logs/', views.logs, name='logs'),
    path('alerts/', views.alerts, name='alerts'),
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
]
