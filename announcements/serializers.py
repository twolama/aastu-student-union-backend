from rest_framework import serializers
from .models import Announcement, AnnouncementCategory
from users.serializers import UserMinimalSerializer

class AnnouncementCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementCategory
        fields = ('id', 'name', 'slug', 'description')

class AnnouncementListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing announcements in lists or feeds.
    Excludes the large 'body' field.
    """
    author = UserMinimalSerializer(read_only=True)
    author_role_name = serializers.CharField(source='author.role_name', read_only=True)
    published_date = serializers.CharField(source='created_at_formatted', read_only=True)
    category_details = AnnouncementCategorySerializer(source='category', read_only=True)
    body_excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'body_excerpt', 'category', 'category_details',
            'is_pinned', 'author', 'author_name', 
            'author_role_name', 'image', 'tags', 'procedure_steps',
            'published_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'published_date', 'author_role_name', 'category_details')

    def get_body_excerpt(self, obj):
        if not obj.body:
            return ""
        # Basic strip tags (optional, but recommended if body is HTML)
        import re
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', obj.body)
        return text[:160] + "..." if len(text) > 160 else text

class AnnouncementDetailSerializer(AnnouncementListSerializer):
    """
    Detailed serializer for single announcement view.
    Includes the full rich-text 'body'.
    """
    class Meta(AnnouncementListSerializer.Meta):
        fields = AnnouncementListSerializer.Meta.fields + ('body',)

class AnnouncementSerializer(AnnouncementDetailSerializer):
    """
    Alias for backward compatibility and internal creation.
    """
    def to_internal_value(self, data):
        """
        Support tags as JSON-string for multipart/form-data.
        """
        import json
        if hasattr(data, 'dict'):
             data = data.copy()

        for field in ['tags', 'procedure_steps']:
            val = data.get(field)
            if isinstance(val, str):
                try:
                    data[field] = json.loads(val)
                except (ValueError, TypeError):
                     pass

        return super().to_internal_value(data)

    def validate_tags(self, value):
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return value

    def validate_procedure_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Procedure steps must be a list of strings/objects.")
        return value
