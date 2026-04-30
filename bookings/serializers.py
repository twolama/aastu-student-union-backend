from datetime import datetime, time
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from clubs.models import Club

class BookingListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing bookings.
    Reduces nested user/club info to essential identifiers.
    """
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    event_title = serializers.CharField(source='title', read_only=True)
    date_label = serializers.SerializerMethodField()
    time_label = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'id_label', 'requester_name', 'club_name', 'venue_name',
            'event_title', 'status', 'start_date', 'end_date', 'selected_slots',
            'requested_date_iso', 'time_range', 'date_label', 'time_label'
        )
        read_only_fields = ('id', 'id_label', 'date_label', 'time_label', 'event_title')

    @extend_schema_field(str)
    def get_date_label(self, obj):
        if obj.start_date and obj.end_date:
            if obj.start_date == obj.end_date:
                return obj.start_date.strftime("%b %d, %Y")
            return f"{obj.start_date.strftime('%b %d, %Y')} - {obj.end_date.strftime('%b %d, %Y')}"
        return obj.requested_date_iso.strftime("%b %d, %Y") if obj.requested_date_iso else None

    @extend_schema_field(str)
    def get_time_label(self, obj):
        if isinstance(obj.selected_slots, list) and obj.selected_slots:
            def format_12h(t_str):
                try:
                    h = int(t_str.split(':')[0])
                    if h == 12: return "12 PM"
                    if h > 12: return f"{h-12} PM"
                    return f"{h} AM"
                except: return t_str
            sorted_slots = sorted(obj.selected_slots)
            if len(sorted_slots) == 1:
                return format_12h(sorted_slots[0])
            return f"{format_12h(sorted_slots[0])} - {format_12h(sorted_slots[-1])}"
        return obj.time_range

class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Full record for booking details.
    Includes full requester and club nested objects.
    """
    requester = UserMinimalSerializer(read_only=True)
    club_details = ClubMinimalSerializer(source='club', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_type = serializers.SerializerMethodField()
    event_title = serializers.CharField(source='title', read_only=True)
    requested_date_iso = serializers.DateTimeField(required=False, allow_null=True)
    time_range = serializers.CharField(required=False, allow_blank=True)
    selected_slots = serializers.ListField(
        child=serializers.RegexField(regex=r'^([01]\d|2[0-3]):[0-5]\d$'),
        required=False,
        allow_empty=True,
    )
    equipment_requested = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    
    # Pre-calculated frontend label helpers
    capacity_label = serializers.CharField(source='venue.capacity_label', read_only=True)
    date_label = serializers.SerializerMethodField()
    time_label = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'id_label', 'requester', 'club', 'club_details', 'venue', 'venue_name', 'venue_type',
            'title', 'event_title', 'status', 'purpose', 'expected_attendance',
            'equipment_requested', 'special_requests', 'guidelines_acknowledged',
            'acknowledged_at', 'start_date', 'end_date', 'selected_slots',
            'requested_date_iso', 'time_range', 'capacity_label', 'date_label',
            'time_label', 'event', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'id_label', 'event', 'created_at', 'updated_at')

    @extend_schema_field(str)
    def get_date_label(self, obj):
        if obj.start_date and obj.end_date:
            if obj.start_date == obj.end_date:
                return obj.start_date.strftime("%b %d, %Y")
            return f"{obj.start_date.strftime('%b %d, %Y')} - {obj.end_date.strftime('%b %d, %Y')}"
        return obj.requested_date_iso.strftime("%b %d, %Y") if obj.requested_date_iso else None

    @extend_schema_field(str)
    def get_time_label(self, obj):
        if isinstance(obj.selected_slots, list) and obj.selected_slots:
            def format_12h(t_str):
                try:
                    h = int(t_str.split(':')[0])
                    if h == 12: return "12 PM"
                    if h > 12: return f"{h-12} PM"
                    return f"{h} AM"
                except: return t_str
            sorted_slots = sorted(obj.selected_slots)
            if len(sorted_slots) == 1:
                return format_12h(sorted_slots[0])
            return f"{format_12h(sorted_slots[0])} - {format_12h(sorted_slots[-1])}"
        return obj.time_range

    @extend_schema_field(str)
    def get_venue_type(self, obj):
        category = getattr(obj.venue, 'category', None)
        return category.name if category else ""

class BookingSerializer(BookingDetailSerializer):
    """
    Alias for creation and backward compatibility.
    """
    club = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.filter(is_active=True),
        required=True,
        allow_null=False,
    )
    title = serializers.CharField(required=True, allow_blank=False)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    selected_slots = serializers.ListField(
        child=serializers.RegexField(regex=r'^([01]\d|2[0-3]):[0-5]\d$'),
        required=True,
        allow_empty=False,
    )
    guidelines_acknowledged = serializers.BooleanField(required=True)
    requested_date_iso = serializers.DateTimeField(read_only=True)
    time_range = serializers.CharField(read_only=True)

    class Meta(BookingDetailSerializer.Meta):
        extra_kwargs = {
            'club': {'required': True, 'allow_null': False},
        }

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        selected_slots = attrs.get('selected_slots', getattr(self.instance, 'selected_slots', []))
        guidelines_acknowledged = attrs.get(
            'guidelines_acknowledged',
            getattr(self.instance, 'guidelines_acknowledged', False)
        )
        requested_date_iso = attrs.get('requested_date_iso', getattr(self.instance, 'requested_date_iso', None))

        is_create = self.instance is None

        if is_create and not attrs.get('title'):
            raise serializers.ValidationError({'title': 'Event title is required.'})

        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})

        if is_create and not requested_date_iso and not start_date:
            raise serializers.ValidationError({
                'start_date': 'Start date is required (or provide legacy requested_date_iso).'
            })

        if is_create and start_date and not end_date:
            raise serializers.ValidationError({'end_date': 'End date is required when start date is provided.'})

        if is_create and not selected_slots:
            raise serializers.ValidationError({'selected_slots': 'At least one time slot must be selected.'})

        if selected_slots:
            unique_slots = sorted(set(selected_slots))
            attrs['selected_slots'] = unique_slots

            # Keep legacy range synchronized for old clients.
            if len(unique_slots) == 1:
                attrs['time_range'] = unique_slots[0]
            else:
                attrs['time_range'] = f"{unique_slots[0]} - {unique_slots[-1]}"

        if start_date and not attrs.get('requested_date_iso'):
            attrs['requested_date_iso'] = timezone.make_aware(datetime.combine(start_date, time.min))

        if is_create and not guidelines_acknowledged:
            raise serializers.ValidationError({
                'guidelines_acknowledged': 'Booking guidelines must be acknowledged.'
            })

        if attrs.get('guidelines_acknowledged') and not attrs.get('acknowledged_at'):
            attrs['acknowledged_at'] = timezone.now()

        return attrs
