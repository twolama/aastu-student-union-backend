from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class MultiIdentifierBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using:
    - Username
    - Email
    - Student ID
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Check for username, email, or student_id
            user = User.objects.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(student_id__iexact=username)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the vulnerability to timing attacks
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # If multiple users match (shouldn't happen with unique constraints), 
            # pick the first one or handle as error
            user = User.objects.filter(
                Q(username__iexact=username) | 
                Q(email__iexact=username) | 
                Q(student_id__iexact=username)
            ).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
