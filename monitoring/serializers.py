from rest_framework import serializers
from .models import ClusterHealth, Metric, Alert, Log

class ClusterHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClusterHealth
        fields = '__all__'

class MetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metric
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = '__all__'
