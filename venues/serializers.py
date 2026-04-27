from rest_framework import serializers
from .models import Venue, VenueCategory, VenueImage

class VenueCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VenueCategory
        fields = ['id', 'name', 'slug', 'description']

class VenueImageSerializer(serializers.ModelSerializer):
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue',
        write_only=True
    )

    class Meta:
        model = VenueImage
        fields = ['id', 'venue', 'venue_id', 'image', 'alt_text']
        read_only_fields = ['venue']

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

    def to_internal_value(self, data):
        """
        Handle stringified JSON in multipart/form-data.
        Ensures both snake_case and camelCase variants from frontend are parsed.
        """
        import json
        if hasattr(data, 'dict'):
            data = data.dict()
        else:
            data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        # Define mappings for common multipart JSON fields
        mappings = {
            'contact': ['contact'],
            'map_coordinates': ['map_coordinates', 'mapCoordinates'],
            'amenities': ['amenities']
        }
        
        for field, variants in mappings.items():
            for variant in variants:
                if variant in data and isinstance(data[variant], (str, bytes)):
                    try:
                        # Parse the JSON string
                        parsed_val = json.loads(data[variant])
                        # Always set the snake_case field that DRF expects
                        data[field] = parsed_val
                        break
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return super().to_internal_value(data)

    def validate_amenities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Amenities must be a list.")
        return value

    def validate_map_coordinates(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Map coordinates must be an object.")
        required_fields = ['lat', 'lng']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required coordinate field: {field}")
            try:
                value[field] = float(value[field])
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Coordinate '{field}' must be numeric.")
        return value

    def validate_contact(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Contact must be an object.")
        required_fields = ['name', 'role', 'phone', 'email']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required contact field: {field}")
        return value
