from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from datetime import datetime, timedelta
from typing import Any, Dict
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from drf_spectacular.utils import extend_schema
from .models import Role
from .serializers import (
    UserSerializer, UserDetailSerializer, SelfProfileSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, ChangePasswordSerializer,
    RoleSerializer,
)

User = get_user_model()


class RoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for user roles.
    Read access is public; write actions are restricted to admins.
    """
    queryset = Role.objects.filter(is_active=True).order_by('name')
    serializer_class = RoleSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login view that returns user details and tokens in a specific format.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({
                "success": False,
                "message": "Login failed",
                "data": None,
                "statusCode": 401,
                "error": str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.user
        tokens = serializer.validated_data
        
        # Calculate expiry dates
        access_expiry = timezone.now() + jwt_settings.ACCESS_TOKEN_LIFETIME
        refresh_expiry = timezone.now() + jwt_settings.REFRESH_TOKEN_LIFETIME

        return Response({
            "success": True,
            "message": "Login successful",
            "data": {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "name": user.name,
                    "studentId": user.student_id,
                    "role": user.role.slug if user.role else None,
                    "email": user.email,
                    "registrationDate": user.date_joined.isoformat(),
                    "status": "Active" if user.is_active else "Inactive",
                },
                "tokens": {
                    "accessToken": {
                        "token": tokens['access'],
                        "expires": access_expiry.isoformat()
                    },
                    "refreshToken": {
                        "token": tokens['refresh'],
                        "expires": refresh_expiry.isoformat()
                    }
                }
            },
            "statusCode": 200,
            "error": None
        })

class ForgotPasswordView(APIView):
    """
    Endpoint to request a password reset email.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = serializer.validated_data # type: ignore
        
        email = data['email']
        
        try:
            user = User.objects.get(email=email)
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Construct reset link (Frontend URL)
            reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            
            # Send email
            # We usegetattr to avoid Pylance issues with custom fields on AbstractUser
            user_display_name = getattr(user, 'name', user.username)
            subject = "Password Reset Requested"
            message = f"Hello {user_display_name},\n\nYou requested a password reset. Click the link below to reset your password:\n\n{reset_link}\n\nIf you did not request this, please ignore this email."
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            # We still return 200 for security reasons (don't reveal registered emails)
            pass

        return Response(
            {"message": "If an account exists with this email, a reset link has been sent."},
            status=status.HTTP_200_OK
        )

class ResetPasswordView(APIView):
    """
    Endpoint to reset password using a token.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = serializer.validated_data # type: ignore
            
        uidb64 = data['uidb64']
        token = data['token']
        password = data['password']

        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            # Check if token is valid
            if not default_token_generator.check_token(user, token):
                return Response(
                    {"error": "Invalid or expired reset link."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(password)
            user.save()
            
            return Response(
                {"message": "Password has been reset successfully."},
                status=status.HTTP_200_OK
            )
            
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid request."},
                status=status.HTTP_400_BAD_REQUEST
            )


class ChangePasswordView(APIView):
    """
    Authenticated endpoint for changing current user's password.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(request=ChangePasswordSerializer)
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self): # type: ignore
        if self.action == 'me':
            return SelfProfileSerializer
        if self.action == 'retrieve':
            return UserDetailSerializer
        return UserSerializer

    @action(detail=False, methods=['get', 'patch'], url_path='me', permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method.lower() == 'get':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = serializer.save()
        
        # Logic to send invitation email
        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            setup_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            
            subject = "Welcome to AASTU Student Union Portal"
            message = f"Hello {user.name},\n\nAn account has been created for you on the AASTU Student Union Portal. Please click the link below to set your password and access your account:\n\n{setup_link}\n\nWelcome aboard!"
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail user creation
            print(f"Failed to send invitation email: {e}")

    def get_queryset(self):
        # Allow filtering by role or department if needed
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset

