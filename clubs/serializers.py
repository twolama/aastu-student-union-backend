from rest_framework import serializers
from .models import Club
from users.serializers import UserMinimalSerializer

class ClubMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal club info for selection/list cards.
    """
    class Meta:
        model = Club
        fields = ('id', 'name', 'category_label', 'logo_label')
        read_only_fields = ('id',)

class ClubSerializer(serializers.ModelSerializer):
    """
    Full Club detail serializer with president's expanded info.
    """
    president = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = Club
        fields = (
            'id', 'name', 'status', 'category_label', 'location_label',
            'logo_label', 'cover_image', 'logo', 'description', 'president',
            'advisor_name', 'links', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def to_internal_value(self, data):
        """
        Support 'links' as a JSON-string for multipart/form-data.
        """
        import json
        
        # Make data mutable if it's a QueryDict (like from multipart/form-data)
        if hasattr(data, 'dict'):
             data = data.copy()

        links = data.get('links')
        if isinstance(links, str):
            try:
                data['links'] = json.loads(links)
            except (ValueError, TypeError):
                 pass # Let DRF's validation capture the error below if needed

        return super().to_internal_value(data)

    def validate_links(self, value):
        """
        Ensure social/external links structure.
        """
        if not isinstance(value, dict):
             raise serializers.ValidationError("Links must be a dict/object (e.g., website: 'url').")
        return value
