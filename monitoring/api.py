from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import ClusterHealth, Metric, Alert, Log
from .serializers import (
    ClusterHealthSerializer,
    MetricSerializer,
    AlertSerializer,
    LogSerializer
)

class ClusterHealthViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClusterHealth.objects.all()
    serializer_class = ClusterHealthSerializer
    filterset_fields = ['cluster', 'status']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get a summary of all cluster health statuses."""
        total = self.queryset.count()
        healthy = self.queryset.filter(status='healthy').count()
        warning = self.queryset.filter(status='warning').count()
        critical = self.queryset.filter(status='critical').count()
        unreachable = self.queryset.filter(status='unreachable').count()
        
        return Response({
            'total': total,
            'healthy': healthy,
            'warning': warning,
            'critical': critical,
            'unreachable': unreachable
        })

class MetricViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Metric.objects.all()
    serializer_class = MetricSerializer
    filterset_fields = ['cluster', 'name', 'type']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get metrics from the last hour."""
        hour_ago = timezone.now() - timedelta(hours=1)
        metrics = self.queryset.filter(timestamp__gte=hour_ago)
        serializer = self.get_serializer(metrics, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get metrics grouped by type."""
        metric_type = request.query_params.get('type', 'system')
        metrics = self.queryset.filter(type=metric_type)
        serializer = self.get_serializer(metrics, many=True)
        return Response(serializer.data)

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    filterset_fields = ['cluster', 'severity', 'status']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert."""
        alert = self.get_object()
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.status = 'acknowledged'
        alert.save()
        return Response({'status': 'alert acknowledged'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert."""
        alert = self.get_object()
        alert.resolved_by = request.user
        alert.resolved_at = timezone.now()
        alert.status = 'resolved'
        alert.save()
        return Response({'status': 'alert resolved'})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active (unresolved) alerts."""
        alerts = self.queryset.exclude(status='resolved')
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)

class LogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    filterset_fields = ['level', 'source']
    search_fields = ['message']
    
    @action(detail=False, methods=['get'])
    def errors(self, request):
        """Get all error and critical logs."""
        error_logs = self.queryset.filter(level__in=['error', 'critical'])
        serializer = self.get_serializer(error_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get logs from the last 24 hours."""
        day_ago = timezone.now() - timedelta(days=1)
        recent_logs = self.queryset.filter(timestamp__gte=day_ago)
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)
