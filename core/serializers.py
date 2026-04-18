from rest_framework import serializers
from .models import College, Department

class CollegeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ('id', 'name', 'abbreviation')

class DepartmentSerializer(serializers.ModelSerializer):
    college_details = CollegeMinimalSerializer(source='college', read_only=True)
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'slug', 'college', 'college_details')
        read_only_fields = ('college_details',)

class CpuStatsSerializer(serializers.Serializer):
    cores = serializers.IntegerField()
    model = serializers.CharField()
    speedMHz = serializers.FloatField()
    loadavg = serializers.ListField(child=serializers.FloatField())

class MemoryStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    free = serializers.IntegerField()
    used = serializers.IntegerField()
    usedPercent = serializers.FloatField()

class DiskStatsSerializer(serializers.Serializer):
    mount = serializers.CharField()
    size = serializers.IntegerField()
    used = serializers.IntegerField()
    available = serializers.IntegerField()
    usedPercent = serializers.FloatField()

class NetworkInterfaceSerializer(serializers.Serializer):
    interface = serializers.CharField()
    state = serializers.CharField()
    speedMbps = serializers.IntegerField()
    incomming = serializers.IntegerField()
    outgoing = serializers.IntegerField()

class SystemStatsDataSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    cpu = CpuStatsSerializer()
    memory = MemoryStatsSerializer()
    disk = DiskStatsSerializer()
    network = NetworkInterfaceSerializer(many=True)
    lastUpdate = serializers.DateTimeField()
    uptime = serializers.FloatField()
    status = serializers.CharField()

class SystemStatsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    response_data = SystemStatsDataSerializer(source='data')
    statusCode = serializers.IntegerField()
    error = serializers.CharField(allow_null=True)

class HealthComponentSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField()

class HealthCheckDataSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    status = serializers.CharField()
    components = HealthComponentSerializer(many=True)

class HealthCheckResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    response_data = HealthCheckDataSerializer(source='data')
    statusCode = serializers.IntegerField()
    error = serializers.CharField(allow_null=True)
