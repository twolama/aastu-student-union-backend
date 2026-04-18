from rest_framework import serializers
from .models import Venue

class VenueListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing venues.
    Excludes full amenities and contact details.
    """
    class Meta:
        model = Venue
        fields = (
            'id', 'name', 'status', 'type_label', 'capacity_label',
            'location', 'image_url', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class VenueDetailSerializer(VenueListSerializer):
    """
    Detailed serializer for single venue view.
    Includes amenities and contact info.
    """
    class Meta(VenueListSerializer.Meta):
        fields = VenueListSerializer.Meta.fields + ('amenities', 'contact')

class VenueSerializer(VenueDetailSerializer):
    """
    Alias for creation and validation.
    """
    def validate_amenities(self, value):
        """
        Ensure amenities is a list of strings as expected by the frontend.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list of strings.")
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Every amenity item must be a string.")
        return value

    def validate_contact(self, value):
        """
        Ensure contact info contains required frontend fields.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Contact must be an object/dict.")
        
        required_fields = ['name', 'role', 'phone', 'email']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required contact field: {field}")
        return value
