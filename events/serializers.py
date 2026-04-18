from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Event
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from venues.serializers import VenueSerializer

class EventSerializer(serializers.ModelSerializer):
    """
    Comprehensive Event Serializer with expanded relations and schedule formatting.
    """
    organizing_club = ClubMinimalSerializer(read_only=True)
    venue = serializers.StringRelatedField() # Or VenueSerializer(read_only=True) if full details are needed
    attendees = UserMinimalSerializer(many=True, read_only=True)
    
    # Computed fields for frontend labels
    date_day = serializers.SerializerMethodField()
    date_month = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(source='attendees.count', read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'summary', 'status', 'is_mega_event',
            'organizing_club', 'venue', 'cover_image',
            'schedule_date', 'schedule_time_range', 'date_day', 'date_month',
            'description', 'attendance', 'attendees', 'attendee_count',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'date_day', 'date_month', 'attendee_count')

    @extend_schema_field(str)
    def get_date_day(self, obj):
        return obj.schedule_date.strftime("%d") if obj.schedule_date else None

    @extend_schema_field(str)
    def get_date_month(self, obj):
        return obj.schedule_date.strftime("%b").upper() if obj.schedule_date else None

    def to_internal_value(self, data):
        """
        Support attendance as JSON-string for multipart/form-data.
        """
        import json
        if hasattr(data, 'dict'):
             data = data.copy()

        attendance = data.get('attendance')
        if isinstance(attendance, str):
            try:
                data['attendance'] = json.loads(attendance)
            except (ValueError, TypeError):
                 pass

        return super().to_internal_value(data)

    def validate_attendance(self, value):
        required = ['current', 'capacity']
        if not isinstance(value, dict) or not all(k in value for k in required):
            raise serializers.ValidationError(f"Must be an object containing at least: {required}")
        return value
