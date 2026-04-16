from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from core.models import SoftDeleteModel

class User(SoftDeleteModel, AbstractUser):
    """
    Custom user model following Next.js frontend requirements.
    Supports roles: su-admin, club-president, general-student.
    """
    ROLE_CHOICES = (
        ('su-admin', 'Student Union Admin'),
        ('club-president', 'Club President'),
        ('general-student', 'General Student'),
    )

    name = models.CharField(max_length=255)
    student_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='general-student')
    avatar_url = models.URLField(null=True, blank=True)
    
    # We use email as second identity but keep username for legacy/internal auth
    email = models.EmailField(unique=True)

    objects: UserManager = UserManager() # type: ignore

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.name} ({self.student_id})"

    @property
    def initials(self) -> str:
        if not self.name:
            return ""
        parts = self.name.split()
        return "".join([p[0].upper() for p in parts[:2]])

