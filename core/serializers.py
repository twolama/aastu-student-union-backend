from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from users.models import Role
from .models import College, Department, SystemNotification


User = get_user_model()

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


class SystemNotificationSerializer(serializers.ModelSerializer):
    target_roles = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    target_users = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        many=True,
        required=False,
    )
    created_by = serializers.UUIDField(read_only=True)

    class Meta:
        model = SystemNotification
        fields = (
            'id',
            'title',
            'description',
            'notification_type',
            'icon_key',
            'href',
            'target_all_users',
            'target_roles',
            'target_users',
            'created_by',
            'expires_at',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        target_all_users = attrs.get('target_all_users', getattr(self.instance, 'target_all_users', False))
        target_roles = attrs.get('target_roles')
        target_users = attrs.get('target_users')

        if target_roles is None and self.instance is not None:
            target_roles = self.instance.target_roles.all()
        if target_users is None and self.instance is not None:
            target_users = self.instance.target_users.all()

        if not target_all_users and not target_roles and not target_users:
            raise serializers.ValidationError(
                'At least one audience target is required: target_all_users, target_roles, or target_users.'
            )
        return attrs


class NotificationItemSerializer(serializers.ModelSerializer):
    unread = serializers.SerializerMethodField()
    time_label = serializers.SerializerMethodField()

    class Meta:
        model = SystemNotification
        fields = (
            'id',
            'title',
            'description',
            'notification_type',
            'icon_key',
            'href',
            'unread',
            'time_label',
            'created_at',
        )

    def get_unread(self, obj):
        read_ids = self.context.get('read_ids', set())
        return obj.id not in read_ids

    def get_time_label(self, obj):
        dt = obj.created_at
        now = timezone.now()
        delta = now - dt
        minutes = int(delta.total_seconds() // 60)

        if minutes < 1:
            return 'Just now'
        if minutes < 60:
            return f"{minutes} min ago"

        hours = int(delta.total_seconds() // 3600)
        if hours < 24:
            return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"

        if (now.date() - dt.date()).days == 1:
            return 'Yesterday'

        return dt.strftime('%b %d')


class MarkNotificationReadSerializer(serializers.Serializer):
    pass


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
