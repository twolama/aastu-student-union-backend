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
        fields = ('id', 'name', 'student_id', 'department', 'role', 'avatar', 'email', 'initials')
        read_only_fields = ('id', 'initials')
