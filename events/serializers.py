from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Event, EventVolunteer
from bookings.models import Booking
from bookings.serializers import BookingDetailSerializer
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from venues.serializers import VenueSerializer, VenueDetailSerializer
from clubs.models import Club

def flatten_logistics_data(val):
    """
    Recursively flattens data that has been corrupted by spreading arrays into objects
    (creating '0', '1', etc. keys).
    """
    if isinstance(val, list):
        return [flatten_logistics_data(i) for i in val]
    if isinstance(val, dict):
        # Check for the common '0' key corruption from JS spreads
        if "0" in val:
            nested = val.pop("0")
            # Recursively flatten the nested part
            flattened_nested = flatten_logistics_data(nested)
            if isinstance(flattened_nested, dict):
                # Merge: outer fields (usually newer) override nested ones
                return {**flattened_nested, **val}
            # If nested wasn't a dict, just keep going with the current dict
        return {k: flatten_logistics_data(v) for k, v in val.items()}
    return val

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
            'attendee_count', 'booking', 'created_at', 'updated_at'
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
    venue_details = VenueDetailSerializer(source='venue', read_only=True)
    booking_details = BookingDetailSerializer(source='booking', read_only=True)

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + (
            'description', 'logistics', 'attendance', 'attendees', 'volunteers', 'venue_details', 'booking_details'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        booking = getattr(instance, 'booking', None)

        if booking and not data.get('venue_details') and getattr(booking, 'venue', None):
            data['venue_details'] = VenueDetailSerializer(booking.venue, context=self.context).data
            if not data.get('venue'):
                data['venue'] = str(booking.venue)
            if not data.get('physical_location_details') and getattr(booking.venue, 'location', None):
                data['physical_location_details'] = booking.venue.location

        if 'logistics' in data and data['logistics']:
            data['logistics'] = flatten_logistics_data(data['logistics'])
        return data

class EventSerializer(EventDetailSerializer):
    """
    Serializer for creation/update and internal logic.
    """
    volunteers = EventVolunteerSerializer(many=True, required=False)
    # Treat logistics and attendance as read-only on input so backend
    # ignores client-supplied values (they are derived from Booking).
    logistics = serializers.JSONField(read_only=True)
    attendance = serializers.JSONField(read_only=True)
    # Keep `organizing_club` representation as the full club object (inherited
    # from EventListSerializer) but provide a write-only `organizing_club_id`
    # field so clients can submit a PK when creating/updating.
    organizing_club_id = serializers.PrimaryKeyRelatedField(
        queryset=Club.objects.all(), write_only=True, source='organizing_club', required=True, allow_null=False
    )

    class Meta(EventDetailSerializer.Meta):
        fields = EventDetailSerializer.Meta.fields + ('organizing_club_id',)

    def _booking_defaults(self, booking):
        venue = getattr(booking, "venue", None)
        venue_name = getattr(venue, "name", None)
        venue_id = str(getattr(venue, "id", "")) if venue else None

        logistics = [
            {
                "venue": venue_name,
                "venue_id": venue_id,
                "booking_id": str(booking.id),
                "equipment": booking.equipment_requested or [],
            }
        ]

        attendance = {
            "current": 0,
            "capacity": booking.expected_attendance or 0,
            "waitlist": 0,
            "vips": 0,
        }

        return logistics, attendance

    def _apply_booking_defaults(self, data):
        booking_value = data.get("booking")
        if not booking_value:
            return data

        booking_id = getattr(booking_value, "pk", booking_value)
        try:
            booking = Booking.objects.select_related("venue").get(pk=booking_id)
        except Booking.DoesNotExist:
            return data

        logistics, attendance = self._booking_defaults(booking)

        if not data.get("logistics"):
            data["logistics"] = logistics
        if not data.get("attendance"):
            data["attendance"] = attendance
        # If organizing club isn't provided, derive it from the booking's club
        # and set the write-only `organizing_club_id` so the serializer will
        # assign the FK without changing the output representation.
        if not data.get("organizing_club") and not data.get("organizing_club_id"):
            booking_club = getattr(booking, "club", None)
            if booking_club:
                data["organizing_club_id"] = booking_club.pk

        return data

    def to_internal_value(self, data):
        """
        Support attendance and logistics as JSON-string for multipart/form-data.
        """
        import json
        if hasattr(data, 'dict'):
            data = data.copy()

        # The frontend posts `organizing_club`, while the serializer field is
        # exposed as `organizing_club_id`. Normalize the payload before DRF
        # validation so the required FK is preserved.
        if data.get('organizing_club') and not data.get('organizing_club_id'):
            data['organizing_club_id'] = data['organizing_club']

        for field in ['attendance', 'logistics', 'volunteers']:
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (ValueError, TypeError):
                    # If the client sends malformed JSON or a non-JSON placeholder,
                    # replace it with a safe default so validation can continue.
                    if field == 'attendance':
                        data[field] = {
                            'current': 0,
                            'capacity': 0,
                            'waitlist': 0,
                            'vips': 0,
                        }
                    elif field == 'logistics':
                        data[field] = []
                    else:
                        data[field] = []

        data = self._apply_booking_defaults(data)

        if not data.get('attendance'):
            data['attendance'] = {
                'current': 0,
                'capacity': 0,
                'waitlist': 0,
                'vips': 0,
            }

        if not data.get('logistics'):
            data['logistics'] = []
        
        # Flatten logistics if it comes in corrupted
        if 'logistics' in data and data['logistics']:
            data['logistics'] = flatten_logistics_data(data['logistics'])

        return super().to_internal_value(data)

    def create(self, validated_data):
        volunteers_data = validated_data.pop('volunteers', [])
        event = Event.objects.create(**validated_data)
        for volunteer_data in volunteers_data:
            EventVolunteer.objects.create(event=event, **volunteer_data)
        return event

    def update(self, instance, validated_data):
        volunteers_data = validated_data.pop('volunteers', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if volunteers_data is not None:
            instance.volunteers.all().delete()
            for volunteer_data in volunteers_data:
                EventVolunteer.objects.create(event=instance, **volunteer_data)
                
        return instance

    def validate_attendance(self, value):
        required = ['current', 'capacity']
        if not isinstance(value, dict) or not all(k in value for k in required):
            raise serializers.ValidationError(f"Must be an object containing at least: {required}")
        return value
