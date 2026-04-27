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
            'is_pinned', 'is_published', 'author', 'author_name', 
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
        import ast
        import json
        if hasattr(data, 'keys'):
            normalized_data = {key: data.get(key) for key in data.keys()}
        else:
            normalized_data = dict(data)

        def coerce_list_field(field_name):
            list_values = data.getlist(field_name) if hasattr(data, 'getlist') else None
            raw_value = normalized_data.get(field_name)

            if list_values and len(list_values) > 1:
                return list(list_values)

            if isinstance(raw_value, (list, tuple)):
                return list(raw_value)

            if not isinstance(raw_value, str):
                return raw_value

            value = raw_value.strip()
            if value == '':
                return []

            try:
                parsed = json.loads(value)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
                return parsed
            except (ValueError, TypeError):
                try:
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, (list, tuple)):
                        return list(parsed)
                except (ValueError, SyntaxError):
                    pass

            # Fallback for unquoted bracket format: [Announcement,AASTU]
            if value.startswith('[') and value.endswith(']'):
                inner = value[1:-1].strip()
                if inner == '':
                    return []

                parts = [part.strip().strip('"\'') for part in inner.split(',')]
                return [part for part in parts if part]

            return raw_value

        for field in ['tags', 'procedure_steps']:
            normalized_data[field] = coerce_list_field(field)

        return super().to_internal_value(normalized_data)

    def validate_tags(self, value):
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return value

    def validate_procedure_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Procedure steps must be a list of strings/objects.")
        return value

    def validate(self, attrs):
        is_published = attrs.get('is_published', getattr(self.instance, 'is_published', False))
        category = attrs.get('category', getattr(self.instance, 'category', None))

        if category == "":
            category = None
            attrs['category'] = None

        if is_published and not category:
            raise serializers.ValidationError({
                'category': ['Category is required when publishing an announcement.']
            })

        return attrs
