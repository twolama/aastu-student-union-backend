from rest_framework import serializers
from .models import Club, ClubCategory
from users.serializers import UserMinimalSerializer
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model

User = get_user_model()

class ClubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubCategory
        fields = ('id', 'name', 'slug', 'description')

class ClubMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal club info for selection/list cards.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Club
        fields = ('id', 'name', 'category', 'category_name', 'logo_label')
        read_only_fields = ('id', 'category_name')

class ClubListSerializer(serializers.ModelSerializer):
    """
    Medium-weight list serializer for the clubs archive.
    Includes essentials plus status and logo.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    president_name = serializers.CharField(source='president.name', read_only=True)
    
    class Meta:
        model = Club
        fields = (
            'id', 'name', 'status', 'category_name', 
            'location_label', 'logo_label', 'logo', 'president_name'
        )
        read_only_fields = ('id', 'category_name', 'president_name')

class ClubDetailSerializer(serializers.ModelSerializer):
    """
    Full Club detail serializer with expanded info.
    Includes nested objects for frontend detail pages.
    """
    # Writeable FKs
    president = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    advisor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    
    # Read-only details
    president_details = UserMinimalSerializer(source='president', read_only=True)
    advisor_details = UserMinimalSerializer(source='advisor', read_only=True)
    category_details = ClubCategorySerializer(source='category', read_only=True)
    
    class Meta:
        model = Club
        fields = (
            'id', 'name', 'status', 'category', 'category_details',
            'location_label', 'logo_label', 'cover_image', 'logo', 'description', 
            'president', 'president_details', 'advisor', 'advisor_details',
            'links', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 
            'category_details', 'president_details', 'advisor_details'
        )

    def to_internal_value(self, data):
        """
        Support 'links' as a JSON-string for multipart/form-data.
        """
        import json
        if hasattr(data, 'dict'):
             data = data.copy()

        links = data.get('links')
        if isinstance(links, str):
            try:
                data['links'] = json.loads(links)
            except (ValueError, TypeError):
                 pass
        return super().to_internal_value(data)

    def validate_links(self, value):
        if not isinstance(value, dict):
             raise serializers.ValidationError("Links must be a dict/object.")
        return value

class ClubSerializer(ClubDetailSerializer):
    """
    Backward-compatible alias.
    """
    pass
