from rest_framework import serializers
from .models import Venue, VenueCategory, VenueImage

class VenueCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueCategory
        fields = ['id', 'name', 'slug', 'description']

class VenueImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueImage
        fields = ['id', 'image', 'alt_text']

class VenueListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing venues.
    """
    category = VenueCategorySerializer(read_only=True)
    
    class Meta:
        model = Venue
        fields = (
            'id', 'name', 'category', 'status', 'max_capacity', 
            'capacity_label', 'campus_block', 'location', 
            'short_description', 'hero_image', 'thumbnail', 
            'image_url', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class VenueDetailSerializer(VenueListSerializer):
    """
    Detailed serializer for single venue view.
    """
    gallery = VenueImageSerializer(many=True, read_only=True)
    amenities = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        help_text="List of venue amenities.",
    )
    contact = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        help_text="Contact object with keys: name, role, phone, email.",
    )
    map_coordinates = serializers.DictField(
        child=serializers.FloatField(),
        required=False,
        help_text="Map coordinates object: {lat: number, lng: number}.",
    )
    
    class Meta(VenueListSerializer.Meta):
        fields = VenueListSerializer.Meta.fields + (
            'floor_level', 'nearby_landmarks', 'full_description',
            'is_publicly_available', 'amenities', 'manager_name',
            'manager_phone', 'manager_email', 'contact', 'gallery',
            'google_maps_url', 'map_coordinates'
        )

class VenueSerializer(VenueDetailSerializer):
    """
    Alias for creation and validation.
    """
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=VenueCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta(VenueDetailSerializer.Meta):
        fields = VenueDetailSerializer.Meta.fields + ('category_id',)

    def validate_amenities(self, value):

        """
        Ensure amenities is a list of strings as expected by the frontend.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list of strings.")
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Every amenity item must be a string.")
        return value

    def validate_map_coordinates(self, value):
        """
        Ensure coordinates are a dict with numeric lat/lng values.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Map coordinates must be an object/dict.")

        required_fields = ['lat', 'lng']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required coordinate field: {field}")
            if not isinstance(value[field], (int, float)):
                raise serializers.ValidationError(f"Coordinate '{field}' must be numeric.")

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
