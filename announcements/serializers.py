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
    published_date = serializers.DateTimeField(source='created_at', format="%Y-%m-%d", read_only=True)

    class Meta:
        model = Announcement
        fields = (
            'id', 'title', 'summary', 'category', 'author', 'author_name', 
            'author_role', 'image_url', 'tags', 'procedure_steps', 
            'content_paragraphs', 'published_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'published_date', 'author_role')

    def validate_tags(self, value):
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError("Tags must be a list of strings.")
        return value

    def validate_procedure_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Procedure steps must be a list of strings/objects.")
        return value

    def validate_content_paragraphs(self, value):
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
             raise serializers.ValidationError("Content paragraphs must be a list of strings.")
        return value
