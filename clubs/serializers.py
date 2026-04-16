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
            'logo_label', 'cover_image_url', 'about', 'president',
            'advisor_name', 'links', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_about(self, value):
        """
        Ensure about is a list of strings (paragraphs) for the frontend.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("About must be a list of strings (paragraphs).")
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError("Every item in the paragraphs list must be a string.")
        return value

    def validate_links(self, value):
        """
        Ensure social/external links structure.
        """
        if not isinstance(value, dict):
             raise serializers.ValidationError("Links must be a dict/object (e.g., website: 'url').")
        return value
