from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
import secrets
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, cast
from django.db.models.query import QuerySet
from django.db import transaction
from rest_framework.request import Request
from urllib.parse import quote_plus
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Role, PasswordResetOTP
from .serializers import (
    UserSerializer, UserDetailSerializer, SelfProfileSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, VerifyResetOTPSerializer,
    ChangePasswordSerializer, RoleSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


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
            error_message = str(e)
            return Response({
                "success": False,
                "message": error_message,
                "data": None,
                "statusCode": 401,
                "error": error_message
            }, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.user
        tokens = cast(Dict[str, Any], serializer.validated_data)
        
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
                    "roles": [role.slug for role in user.roles.all()],
                    "email": user.email,
                    "mustChangePassword": user.must_change_password,
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

def send_password_reset_otp(user):
    otp = f"{secrets.randbelow(10**6):06d}"
    expires_at = timezone.now() + timedelta(minutes=15)
    PasswordResetOTP.objects.create(user=user, otp=otp, expires_at=expires_at)

    verify_link = f"{settings.FRONTEND_URL}/reset-password/verify?email={quote_plus(user.email)}"
    user_display_name = getattr(user, 'name', user.username)
    subject = "Password Reset Code"
    message = (
        f"Hello {user_display_name},\n\n"
        f"You requested a password reset. Use the 6-digit code below to verify your email and set a new password:\n\n"
        f"{otp}\n\n"
        f"Enter this code on the password verification page:\n{verify_link}\n\n"
        "This code expires in 15 minutes. If you did not request this, please ignore this email."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

class ForgotPasswordView(APIView):
    """
    Endpoint to request a password reset code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = cast(Dict[str, Any], serializer.validated_data)

        email = data['email']
        
        try:
            user = User.objects.get(email=email)
            send_password_reset_otp(user)
        except User.DoesNotExist:
            pass

        return Response(
            {"message": "If an account exists with this email, a reset code has been sent."},
            status=status.HTTP_200_OK
        )

class ResendResetOTPView(APIView):
    """
    Endpoint to resend a password reset code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = cast(Dict[str, Any], serializer.validated_data)
        email = data['email']

        try:
            user = User.objects.get(email=email)
            send_password_reset_otp(user)
        except User.DoesNotExist:
            pass

        return Response(
            {"message": "If an account exists with this email, a new reset code has been sent."},
            status=status.HTTP_200_OK
        )

class VerifyResetOTPView(APIView):
    """
    Endpoint to verify a password reset code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyResetOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = cast(Dict[str, Any], serializer.validated_data)
        email = data['email']
        otp = data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid or expired reset code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_record = PasswordResetOTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
            otp=otp,
        ).order_by('-created_at').first()

        if not otp_record:
            recent_otp = PasswordResetOTP.objects.filter(
                user=user,
                is_used=False,
                expires_at__gt=timezone.now(),
            ).order_by('-created_at').first()
            if recent_otp:
                recent_otp.attempts += 1
                recent_otp.save(update_fields=['attempts'])

            return Response(
                {"error": "Invalid or expired reset code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Reset code verified."},
            status=status.HTTP_200_OK
        )

class ResetPasswordView(APIView):
    """
    Endpoint to reset password using an email verification code.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data: Dict[str, Any] = cast(Dict[str, Any], serializer.validated_data)
        email = data['email']
        otp = data['otp']
        password = data['password']

        try:
            user = User.objects.get(email=email)
            otp_record = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at').first()

            if not otp_record:
                return Response(
                    {"error": "Invalid or expired reset code."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])

            reset_user = cast(Any, user)
            reset_user.set_password(password)
            reset_user.must_change_password = False
            reset_user.save(update_fields=['password', 'must_change_password'])
            
            return Response(
                {"message": "Password has been reset successfully."},
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
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

    @extend_schema(request=ChangePasswordSerializer, tags=['Authentication'])
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        data: Dict[str, Any] = cast(Dict[str, Any], serializer.validated_data)

        current_user = cast(Any, request.user)
        current_user.set_password(data['new_password'])
        current_user.must_change_password = False
        current_user.save(update_fields=['password', 'must_change_password'])

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )

@extend_schema(
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Search by name, student ID, email or username"),
        OpenApiParameter("role", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by role ID or slug"),
        OpenApiParameter("department", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by department ID"),
    ]
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
    def me(self, request: Request):
        if request.method.lower() == 'get':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = serializer.save()
            temp_password = secrets.token_urlsafe(9)

            user.set_password(temp_password)
            user.must_change_password = True
            user.save(update_fields=['password', 'must_change_password'])

            subject = "Welcome to AASTU Student Union Portal"
            message = (
                f"Hello {user.name},\n\n"
                "An account has been created for you on the AASTU Student Union Portal.\n\n"
                f"Temporary password: {temp_password}\n\n"
                "Sign in using your username, student ID, or email with this temporary password. "
                "You will be required to change it immediately after login.\n\n"
                "Welcome aboard!"
            )

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                logger.exception("Failed to send invitation email for newly created user", extra={"user_id": str(user.pk), "email": user.email})
                raise serializers.ValidationError({
                    "email": [
                        "Temporary password email could not be sent. User account was not created."
                    ]
                })

    def get_queryset(self) -> Any:
        queryset = self.queryset
        req = cast(Request, self.request)

        # Filter by role (UUID or slug)
        role = req.query_params.get('role')
        if role and role != 'all':
            if len(role) > 30: # Likely a UUID
                queryset = queryset.filter(roles__id=role)
            else:
                queryset = queryset.filter(roles__slug=role)
            queryset = queryset.distinct()

        # Filter by department
        department = req.query_params.get('department')
        if department and department != 'all':
            queryset = queryset.filter(department_id=department)

        # Search functionality
        search = req.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(student_id__icontains=search) | 
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )

        return queryset.order_by('name')

