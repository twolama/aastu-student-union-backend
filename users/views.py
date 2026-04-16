from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, ForgotPasswordSerializer, ResetPasswordSerializer

User = get_user_model()

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
                    "role": user.role,
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
        # Logic to send email would go here
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
        # Logic to verify token and update password would go here
        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK
        )

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Allow filtering by role or department if needed
        queryset = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        return queryset

