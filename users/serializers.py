from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Role
from core.serializers import DepartmentSerializer, CollegeMinimalSerializer

User = get_user_model()

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'slug', 'description', 'is_staff_role')

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)


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
    class Meta:
        model = User
        fields = (
            'id',
            'name',
            'student_id',
            'department',
            'role',
            'avatar',
            'email',
            'phone_number',
            'initials',
            'username',
            'bio',
        )
        read_only_fields = ('id', 'initials')
        extra_kwargs = {
            'username': {'required': False},
        }

    def to_internal_value(self, data):
        """
        Backward compatibility for clients sending `phone` instead of `phone_number`.
        """
        if hasattr(data, 'copy'):
            data = data.copy()
        if 'phone_number' not in data and 'phone' in data:
            data['phone_number'] = data.get('phone')
        return super().to_internal_value(data)

    def create(self, validated_data):
        # Default username to student_id or email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('student_id') or validated_data.get('email')
        
        # Create user without password (will be set via invitation/reset)
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        return user

class UserDetailSerializer(UserSerializer):
    """
    Detailed user data with expanded department, college and role info.
    """
    department_details = DepartmentSerializer(source='department', read_only=True)
    role_details = RoleSerializer(source='role', read_only=True)
    
    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'phone_number', 'dorm_block', 'dorm_room', 
            'department_details', 'role_details', 'is_active', 
            'is_staff', 'date_joined', 'last_login'
        )
        read_only_fields = UserSerializer.Meta.read_only_fields + (
            'department_details', 'role_details', 'date_joined', 'last_login'
        )


class SelfProfileSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    role_details = RoleSerializer(source='role', read_only=True)
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
            'role',
            'role_details',
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
            'initials',
        )

    def to_internal_value(self, data):
        # Backward compatibility for clients sending `phone`.
        if hasattr(data, 'copy'):
            data = data.copy()
        if 'phone_number' not in data and 'phone' in data:
            data['phone_number'] = data.get('phone')
        return super().to_internal_value(data)

