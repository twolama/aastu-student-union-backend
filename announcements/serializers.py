from rest_framework import serializers
from .models import Announcement
from users.serializers import UserMinimalSerializer

class AnnouncementSerializer(serializers.ModelSerializer):
    """
    Serializer for announcements mapping JSONFields to frontend arrays and
    formatting relative/ISO time.
    """
    author = UserMinimalSerializer(read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    published_date = serializers.CharField(source='created_at_formatted', read_only=True)

    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'summary', 'category', 'author', 'author_name', 
            'author_role', 'image', 'tags', 'procedure_steps', 
            'body', 'published_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'published_date', 'author_role')

    def to_internal_value(self, data):
        """
        Support tags and procedure_steps as JSON-string for multipart/form-data.
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
