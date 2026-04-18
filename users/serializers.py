from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)

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
        fields = ('id', 'name', 'student_id', 'department', 'role', 'avatar', 'email', 'initials', 'username')
        read_only_fields = ('id', 'initials')
        extra_kwargs = {
            'username': {'required': False},
        }

    def create(self, validated_data):
        # Default username to student_id or email if not provided
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('student_id') or validated_data.get('email')
        
        # Create user without password (will be set via invitation/reset)
        user = User.objects.create_user(**validated_data)
        user.set_unusable_password()
        user.save()
        return user

