from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Event, EventVolunteer
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from venues.serializers import VenueSerializer

class EventVolunteerSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = EventVolunteer
        fields = (
            'id', 'user', 'event', 'full_name', 'student_id', 
            'phone', 'email', 'role', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class EventListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for event cards.
    Excludes attendees, volunteers, description, and logistics.
    """
    organizing_club = ClubMinimalSerializer(read_only=True)
    venue = serializers.StringRelatedField()
    date_day = serializers.SerializerMethodField()
    date_month = serializers.SerializerMethodField()
    attendee_count = serializers.IntegerField(source='attendees.count', read_only=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'short_description', 'status', 'is_mega_event',
            'is_archived', 'max_capacity',
            'organizing_club', 'venue', 'physical_location_details',
            'cover_image', 'start_date_time', 'end_date_time',
            'date_day', 'date_month', 'registration_link',
            'attendee_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'date_day', 'date_month', 'attendee_count')

    @extend_schema_field(str)
    def get_date_day(self, obj):
        return obj.start_date_time.strftime("%d") if obj.start_date_time else None

    @extend_schema_field(str)
    def get_date_month(self, obj):
        return obj.start_date_time.strftime("%b").upper() if obj.start_date_time else None

class EventDetailSerializer(EventListSerializer):
    """
    Full record for event detail pages.
    """
    attendees = UserMinimalSerializer(many=True, read_only=True)
    volunteers = EventVolunteerSerializer(many=True, read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + (
            'description', 'logistics', 'attendance', 'attendees', 'volunteers'
        )

class EventSerializer(EventDetailSerializer):
    """
    Serializer for creation/update and internal logic.
    """
    volunteers = EventVolunteerSerializer(many=True, required=False)

    def to_internal_value(self, data):
        """
        Support attendance and logistics as JSON-string for multipart/form-data.
        """
        import json
        if hasattr(data, 'dict'):
             data = data.copy()

        for field in ['attendance', 'logistics', 'volunteers']:
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (ValueError, TypeError):
                     pass

        return super().to_internal_value(data)

    def create(self, validated_data):
        volunteers_data = validated_data.pop('volunteers', [])
        event = Event.objects.create(**validated_data)
        for volunteer_data in volunteers_data:
            EventVolunteer.objects.create(event=event, **volunteer_data)
        return event

    def validate_attendance(self, value):
        required = ['current', 'capacity']
        if not isinstance(value, dict) or not all(k in value for k in required):
            raise serializers.ValidationError(f"Must be an object containing at least: {required}")
        return value
