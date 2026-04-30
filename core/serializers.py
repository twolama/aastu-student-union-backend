from rest_framework import serializers
from .models import College, Department

class CollegeMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ('id', 'name', 'abbreviation')


class CollegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ('id', 'name', 'abbreviation', 'description')

class DepartmentSerializer(serializers.ModelSerializer):
    college_details = CollegeMinimalSerializer(source='college', read_only=True)
    
    class Meta:
        model = Department
        fields = ('id', 'name', 'slug', 'college', 'college_details')
        read_only_fields = ('college_details',)


class AnalyticsStatCardSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    value = serializers.CharField()
    trend = serializers.CharField()
    trend_direction = serializers.ChoiceField(choices=['up', 'down', 'neutral'])
    icon = serializers.CharField()
    icon_bg = serializers.CharField()


class AnalyticsTrendPointSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.FloatField()


class AnalyticsBreakdownItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    color = serializers.CharField()


class AnalyticsVenueKpiSerializer(serializers.Serializer):
    most_popular = serializers.CharField()
    avg_session_hours = serializers.FloatField()


class AnalyticsSimpleStatSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    value = serializers.CharField()
    icon = serializers.CharField()


class AnalyticsActivitySerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    bold_label = serializers.CharField()
    description = serializers.CharField()
    timestamp = serializers.CharField()


class AnalyticsEventAttendeeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()


class AnalyticsUpcomingEventSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    venue = serializers.CharField()
    image_url = serializers.CharField()
    date_label = serializers.CharField()
    attendee_count = serializers.IntegerField()
    attendees = AnalyticsEventAttendeeSerializer(many=True)


class AnalyticsDashboardDataSerializer(serializers.Serializer):
    period = serializers.CharField()
    overview = AnalyticsStatCardSerializer(many=True)
    registration_trends = AnalyticsTrendPointSerializer(many=True)
    occupancy_trends = AnalyticsTrendPointSerializer(many=True)
    club_breakdown = AnalyticsBreakdownItemSerializer(many=True)
    event_distribution = AnalyticsBreakdownItemSerializer(many=True)
    venue_kpis = AnalyticsVenueKpiSerializer()
    venue_stats = AnalyticsSimpleStatSerializer(many=True)
    club_stats = AnalyticsSimpleStatSerializer(many=True)
    recent_activity = AnalyticsActivitySerializer(many=True)
    upcoming_mega_events = AnalyticsUpcomingEventSerializer(many=True)


class AnalyticsDashboardResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = AnalyticsDashboardDataSerializer()
    statusCode = serializers.IntegerField()
    error = serializers.CharField(allow_null=True)

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
