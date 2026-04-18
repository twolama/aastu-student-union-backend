from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from venues.serializers import VenueSerializer

class BookingListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing bookings.
    Reduces nested user/club info to essential identifiers.
    """
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    club_name = serializers.CharField(source='club.name', read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    date_label = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'id_label', 'requester_name', 'club_name', 'venue_name',
            'status', 'requested_date_iso', 'time_range', 'date_label'
        )
        read_only_fields = ('id', 'id_label', 'date_label')

    @extend_schema_field(str)
    def get_date_label(self, obj):
        return obj.requested_date_iso.strftime("%b %d, %Y") if obj.requested_date_iso else None

class BookingDetailSerializer(serializers.ModelSerializer):
    """
    Full record for booking details.
    Includes full requester and club nested objects.
    """
    requester = UserMinimalSerializer(read_only=True)
    club = ClubMinimalSerializer(read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_type = serializers.CharField(source='venue.type_label', read_only=True)
    
    # Pre-calculated frontend label helpers
    capacity_label = serializers.CharField(source='venue.capacity_label', read_only=True)
    date_label = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            'id', 'id_label', 'requester', 'club', 'venue', 'venue_name', 'venue_type',
            'status', 'purpose', 'expected_attendance', 'equipment_requested',
            'special_requests', 'requested_date_iso', 'time_range',
            'capacity_label', 'date_label', 'event', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'id_label', 'event', 'created_at', 'updated_at')

    @extend_schema_field(str)
    def get_date_label(self, obj):
        return obj.requested_date_iso.strftime("%b %d, %Y") if obj.requested_date_iso else None

class BookingSerializer(BookingDetailSerializer):
    """
    Alias for creation and backward compatibility.
    """
    pass
