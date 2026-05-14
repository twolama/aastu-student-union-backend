from rest_framework import viewsets, permissions, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
import threading
import secrets
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, cast
from django.db.models.query import QuerySet
from django.db import transaction
from rest_framework.request import Request
from urllib.parse import quote_plus
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.template.loader import render_to_string
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Role, PasswordResetOTP
from .permissions import permissions_to_frontend_keys
from .serializers import (
    UserSerializer, UserDetailSerializer, SelfProfileSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, VerifyResetOTPSerializer,
    ChangePasswordSerializer, RoleSerializer, UserPermissionsResponseSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _send_user_invitation_email(user_id: str, recipient_email: str, recipient_name: str, temporary_password: str) -> None:
    """
    Send a temporary password invitation email to a newly created user.
    Includes detailed logging for diagnosis and retry logic with exponential backoff.
    """
    if not recipient_email:
        logger.warning(
            "Skipping invitation email because recipient email is empty",
            extra={"user_id": user_id},
        )
        return

    # Check if email is properly configured
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        logger.error(
            "Email not sent: EMAIL_HOST_USER or EMAIL_HOST_PASSWORD not configured",
            extra={"user_id": user_id, "email": recipient_email},
        )
        return

    subject = "Welcome to AASTU Student Union Portal"
    base_frontend_url = settings.FRONTEND_URL.rstrip('/')
    context = {
        'recipient_name': recipient_name or 'Student',
        'temporary_password': temporary_password,
        'login_url': f'{base_frontend_url}/login',
        'logo_url': f'{base_frontend_url}/aastu_logo.jpg',
        'brand_primary': '#c49a22',
        'brand_primary_dark': '#a67f18',
        'brand_dark': '#14213d',
        'brand_bg': '#f7f8fc',
        'brand_card': '#ffffff',
        'brand_border': '#e7ebf3',
        'brand_text': '#51607e',
        'brand_text_dark': '#14213d',
        'brand_button_hover': '#1d2f57',
        'support_email': settings.DEFAULT_FROM_EMAIL,
        'current_year': timezone.now().year,
    }

    try:
        text_message = render_to_string('users/emails/new_account_invitation.txt', context)
        html_message = render_to_string('users/emails/new_account_invitation.html', context)
    except Exception as e:
        logger.error(
            f"Failed to render email templates: {str(e)}",
            extra={"user_id": user_id, "email": recipient_email},
            exc_info=True,
        )
        return

    from_email = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL

    # Retry a few times to survive transient SMTP/network hiccups.
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                f"Attempting to send invitation email (attempt {attempt}/{max_attempts})",
                extra={"user_id": user_id, "email": recipient_email, "from_email": from_email},
            )
            email_message = EmailMultiAlternatives(
                subject,
                text_message,
                from_email,
                [recipient_email],
            )
            email_message.attach_alternative(html_message, 'text/html')
            result = email_message.send(fail_silently=False)
            logger.info(
                f"Invitation email sent successfully (result: {result})",
                extra={"user_id": user_id, "email": recipient_email, "attempt": attempt},
            )
            return
        except Exception as e:
            logger.warning(
                f"Failed to send invitation email (attempt {attempt}/{max_attempts}): {str(e)}",
                extra={"user_id": user_id, "email": recipient_email, "attempt": attempt},
                exc_info=True,
            )
            if attempt < max_attempts:
                time.sleep(1.5 * attempt)
    
    # If all retries failed, log final error
    logger.error(
        f"Failed to send invitation email after {max_attempts} attempts",
        extra={"user_id": user_id, "email": recipient_email},
    )


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

        user = User.objects.select_related('department').prefetch_related('roles__groups__permissions__content_type').get(pk=serializer.user.pk)
        tokens = cast(Dict[str, Any], serializer.validated_data)
        django_permissions = sorted(user.get_all_permissions())
        frontend_permissions = permissions_to_frontend_keys(django_permissions)
        
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
                    "avatar": user.avatar.url if user.avatar else None,
                    "role": user.role.slug if user.role else None,
                    "roles": [role.slug for role in user.roles.all()],
                    "permissions": frontend_permissions,
                    "djangoPermissions": django_permissions,
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

    def dispatch_reset_email():
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Password reset email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}", exc_info=True)

    # Dispatch email in a background thread to avoid blocking the request
    # and triggering worker timeouts on platforms like Render.
    thread = threading.Thread(target=dispatch_reset_email, daemon=True)
    thread.start()

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
    queryset = User.objects.filter(is_active=True).select_related('department').prefetch_related('roles__groups__permissions__content_type')
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
            # Re-fetch the user with all necessary data for the serializer to avoid N+1 queries
            user = User.objects.select_related('department', 'department__college') \
                .prefetch_related('roles__groups__permissions__content_type') \
                .get(pk=request.user.pk)
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Create a new user and send an invitation email with temporary password.
        Email is sent asynchronously in background daemon thread for instant response.
        """
        with transaction.atomic():
            user = serializer.save()
            temp_password = secrets.token_urlsafe(9)

            logger.info(
                "Creating new user, will send invitation email",
                extra={"user_id": str(user.pk), "email": user.email, "name": user.name},
            )

            user.set_password(temp_password)
            user.must_change_password = True
            user.save(update_fields=['password', 'must_change_password'])

            def dispatch_invitation_email() -> None:
                try:
                    logger.info(
                        "Dispatching invitation email in background daemon thread",
                        extra={"user_id": str(user.pk), "email": user.email},
                    )
                    _send_user_invitation_email(
                        str(user.pk), user.email, user.name, temp_password
                    )
                except Exception as e:
                    logger.error(
                        f"Error in email dispatch thread: {str(e)}",
                        extra={"user_id": str(user.pk), "email": user.email},
                        exc_info=True,
                    )

            # Start background daemon thread for fire-and-forget behavior
            # Returns immediately without waiting for email to send
            def start_email_thread() -> None:
                thread = threading.Thread(
                    target=dispatch_invitation_email,
                    daemon=True,  # Daemon thread: returns instantly, doesn't block
                    name=f"email-invitation-{user.pk}",
                )
                thread.start()

            # Use transaction.on_commit to ensure user is saved before email thread starts
            transaction.on_commit(start_email_thread)

    def perform_destroy(self, instance):
        if instance.is_superuser:
            raise PermissionDenied('Superuser accounts cannot be deleted.')
        if instance.pk == self.request.user.pk and self.request.user.is_superuser:
            raise PermissionDenied('Superuser accounts cannot be deleted.')
        instance.delete()

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


class UserPermissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=UserPermissionsResponseSerializer, tags=['Authentication'])
    def get(self, request: Request, user_id: str):
        if str(request.user.pk) != str(user_id) and not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {"detail": "You do not have permission to view these permissions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        django_permissions = sorted(user.get_all_permissions())
        return Response(
            {
                "success": True,
                "message": "Permissions retrieved successfully.",
                "data": {
                    "userId": str(user.pk),
                    "permissions": permissions_to_frontend_keys(django_permissions),
                    "djangoPermissions": django_permissions,
                },
            }
        )

