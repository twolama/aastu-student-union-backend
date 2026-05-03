from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from typing import Any, cast
from .models import Role
from .permissions import permissions_to_frontend_keys
from core.serializers import DepartmentSerializer, CollegeMinimalSerializer

User = get_user_model()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'slug', 'description', 'is_staff_role')

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class VerifyResetOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        validate_password(attrs['password'])
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_current_password(self, value):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'New password and confirm password do not match.'
            })

        request = self.context.get('request')
        user = request.user if request else None
        validate_password(attrs['new_password'], user=user)
        return attrs

class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Simplified user data for embedding in lists or other models.
    """
    class Meta:
        model = User
        fields = ('id', 'name', 'avatar', 'initials')
        read_only_fields = ('id', 'initials')

class UserSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    roles = serializers.PrimaryKeyRelatedField(many=True, queryset=Role.objects.all(), required=False)
    role = serializers.ReadOnlyField(source='role.slug')
    permissions = serializers.SerializerMethodField()
    django_permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'name',
            'student_id',
            'department',
            'department_name',
            'roles',
            'role',
            'permissions',
            'django_permissions',
            'avatar',
            'email',
            'phone_number',
            'initials',
            'username',
            'bio',
            'dorm_block',
            'dorm_room',
        )
        read_only_fields = ('id', 'initials', 'department_name', 'role')
        extra_kwargs = {
            'username': {'required': False},
        }

    def to_internal_value(self, data):
        """
        Backward compatibility for clients sending `phone` instead of `phone_number`
        and `role` instead of `roles`.
        """
        if hasattr(data, 'copy'):
            data = data.copy()
        if 'phone_number' not in data and 'phone' in data:
            data['phone_number'] = data.get('phone')
        if 'role' in data and 'roles' not in data:
            data['roles'] = [data.get('role')] if data.get('role') is not None else []
        return super().to_internal_value(data)

    def create(self, validated_data):
        roles = validated_data.pop('roles', [])

        # Default username to student_id or email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('student_id') or validated_data.get('email')

        # Password is assigned by onboarding flow in the view layer.
        user = cast(Any, User.objects.create_user(**validated_data))
        member_role = Role.objects.filter(slug__iexact='member').first() or Role.objects.filter(name__iexact='member').first()
        if member_role and member_role not in roles:
            roles = [member_role, *roles]
        if roles:
            user.roles.set(roles)
        return user

    def update(self, instance, validated_data):
        roles = validated_data.pop('roles', None)
        user = super().update(instance, validated_data)
        if roles is not None:
            user.roles.set(roles)
        return user

    def get_permissions(self, obj) -> list[str]:
        return permissions_to_frontend_keys(obj.get_all_permissions())

    def get_django_permissions(self, obj) -> list[str]:
        return sorted(obj.get_all_permissions())

class UserDetailSerializer(UserSerializer):
    """
    Detailed user data with expanded department, college and role info.
    """
    department_details = DepartmentSerializer(source='department', read_only=True)
    role_details = RoleSerializer(source='role', read_only=True)
    roles_details = RoleSerializer(source='roles', many=True, read_only=True)
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'phone_number', 'dorm_block', 'dorm_room', 
            'department_details', 'role_details', 'roles_details', 'is_active', 
            'is_staff', 'date_joined', 'last_login'
        )
        read_only_fields = UserSerializer.Meta.read_only_fields + (
            'department_details', 'role_details', 'roles_details', 'date_joined', 'last_login'
        )


class SelfProfileSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    role_details = RoleSerializer(source='role', read_only=True)
    roles_details = RoleSerializer(source='roles', many=True, read_only=True)
    role = serializers.CharField(source='role.slug', read_only=True)
    permissions = serializers.SerializerMethodField()
    django_permissions = serializers.SerializerMethodField()
    college = serializers.UUIDField(source='department.college_id', read_only=True)
    college_details = CollegeMinimalSerializer(source='department.college', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'name',
            'student_id',
            'email',
            'avatar',
            'phone_number',
            'dorm_block',
            'dorm_room',
            'department',
            'department_details',
            'college',
            'college_details',
            'roles',
            'role',
            'role_details',
            'roles_details',
            'permissions',
            'django_permissions',
            'initials',
            'bio',
        )
        read_only_fields = (
            'id',
            'student_id',
            'email',
            'department_details',
            'college',
            'college_details',
            'role',
            'role_details',
            'roles_details',
            'permissions',
            'django_permissions',
            'initials',
        )

    def to_internal_value(self, data):
        # Backward compatibility for clients sending `phone`.
        if hasattr(data, 'copy'):
            data = data.copy()
        if 'phone_number' not in data and 'phone' in data:
            data['phone_number'] = data.get('phone')
        return super().to_internal_value(data)

    def get_permissions(self, obj) -> list[str]:
        return permissions_to_frontend_keys(obj.get_all_permissions())

    def get_django_permissions(self, obj) -> list[str]:
        return sorted(obj.get_all_permissions())


class UserPermissionsDataSerializer(serializers.Serializer):
    userId = serializers.UUIDField()
    permissions = serializers.ListField(child=serializers.CharField())
    djangoPermissions = serializers.ListField(child=serializers.CharField())


class UserPermissionsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()

    def get_fields(self):
        fields = super().get_fields()
        fields['data'] = UserPermissionsDataSerializer()
        return fields

