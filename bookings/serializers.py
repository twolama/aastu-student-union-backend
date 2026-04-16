from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import Booking
from users.serializers import UserMinimalSerializer
from clubs.serializers import ClubMinimalSerializer
from venues.serializers import VenueSerializer

class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for booking requests with expanded relational info.
    Includes requester and club details for admin views.
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
            'status', 'purpose', 'requested_date_iso', 'time_range',
            'capacity_label', 'date_label', 'event', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'id_label', 'event', 'created_at', 'updated_at')

    @extend_schema_field(str)
    def get_date_label(self, obj):
        return obj.requested_date_iso.strftime("%b %d, %Y") if obj.requested_date_iso else None
