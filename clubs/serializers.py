from rest_framework import serializers
from .models import Club, ClubCategory
from users.serializers import UserMinimalSerializer
from drf_spectacular.utils import extend_schema_field
from core.serializers import DepartmentSerializer
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
    department_name = serializers.CharField(source='department.name', read_only=True)
    president_name = serializers.CharField(source='president.name', read_only=True)
    advisor_name = serializers.CharField(source='advisor.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    @extend_schema_field(serializers.IntegerField())
    def get_member_count(self, obj):
        # Placeholder until Membership model is implemented
        return 0
    
    class Meta:
        model = Club
        fields = (
            'id', 'name', 'status', 'category_name', 'department_name',
            'location_label', 'logo_label', 'logo', 'cover_image', 
            'president_name', 'advisor_name', 'department', 'description',
            'member_count', 'proposal_file', 'show_proposal'
        )
        read_only_fields = ('id', 'category_name', 'department_name', 'president_name', 'advisor_name')

class FlexibleJSONField(serializers.JSONField):
    """
    Custom JSONField that can handle JSON strings (from multipart/form-data)
    or already-parsed JSON objects/dicts.
    """
    def to_internal_value(self, data):
        if isinstance(data, str) and data.strip():
            import json
            try:
                return json.loads(data)
            except (ValueError, TypeError):
                self.fail('invalid')
        return super().to_internal_value(data)

class UserClubContactSerializer(serializers.ModelSerializer):
    """
    User data for club contacts (President/Advisor) with contact info.
    """
    department_name = serializers.CharField(source='department.name', read_only=True)
    class Meta:
        model = User
        fields = (
            'id', 'name', 'avatar', 'initials', 'email', 
            'phone_number', 'department_name', 'dorm_block', 'dorm_room'
        )
        read_only_fields = ('id', 'initials', 'department_name')

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
    president_details = UserClubContactSerializer(source='president', read_only=True)
    advisor_details = UserClubContactSerializer(source='advisor', read_only=True)
    category_details = ClubCategorySerializer(source='category', read_only=True)
    department_details = DepartmentSerializer(source='department', read_only=True)
    links = FlexibleJSONField(required=False, default=dict)
    
    class Meta:
        model = Club
        fields = (
            'id', 'name', 'status', 'category', 'category_details',
            'department', 'department_details',
            'location_label', 'logo_label', 'cover_image', 'logo', 'description', 
            'president', 'president_details', 'advisor', 'advisor_details',
            'links', 'proposal_file', 'show_proposal', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 
            'category_details', 'president_details', 'advisor_details',
            'department_details'
        )

    def validate_links(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
             raise serializers.ValidationError("Links must be a dictionary/object.")
        return value

class ClubSerializer(ClubDetailSerializer):
    """
    Backward-compatible alias.
    """
    pass
