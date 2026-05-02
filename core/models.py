from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class ActiveManager(models.Manager):
    """Custom manager for soft-delete filtering."""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class BaseModel(models.Model):
    """
    Abstract base model that uses UUID for primary key and inclusion of 
    audit fields (created_at, updated_at).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    @property
    def created_at_formatted(self):
        return self.created_at.strftime("%Y-%m-%d") if self.created_at else ""

class SoftDeleteModel(BaseModel):
    """
    Abstract model for soft-delete logic.
    """
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = models.Manager()          # All objects
    active = ActiveManager()            # Filtered active objects

    class Meta(BaseModel.Meta):
        abstract = True

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_active = True
        self.deleted_at = None
        self.save()

class College(SoftDeleteModel):
    """
    Representation of AASTU Colleges (e.g., COEC, CONAS).
    """
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True) # e.g., COEC
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"

class Department(SoftDeleteModel):
    """
    Academic departments under a college.
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='departments')

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name


class SystemNotification(SoftDeleteModel):
    """
    Persistent system notification that can target all users, specific roles, and/or specific users.
    """

    class NotificationType(models.TextChoices):
        SYSTEM = 'system', 'System'
        ALERT = 'alert', 'Alert'
        BOOKING = 'booking', 'Booking'
        ANNOUNCEMENT = 'announcement', 'Announcement'
        SECURITY = 'security', 'Security'

    title = models.CharField(max_length=180)
    description = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    icon_key = models.CharField(max_length=60, blank=True)
    href = models.CharField(max_length=255, blank=True)
    target_all_users = models.BooleanField(default=False)
    target_roles = models.ManyToManyField('users.Role', blank=True, related_name='system_notifications')
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='targeted_system_notifications')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_system_notifications',
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'System Notification'
        verbose_name_plural = 'System Notifications'
        indexes = [
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return self.title


class NotificationReadState(models.Model):
    """
    Tracks whether a user has read a specific notification.
    """

    notification = models.ForeignKey(SystemNotification, on_delete=models.CASCADE, related_name='read_states')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_read_states')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification Read State'
        verbose_name_plural = 'Notification Read States'
        constraints = [
            models.UniqueConstraint(fields=['notification', 'user'], name='core_notification_user_read_unique'),
        ]
        indexes = [
            models.Index(fields=['user', 'read_at']),
            models.Index(fields=['notification', 'user']),
        ]

    def __str__(self):
        return f"{self.user_id} read {self.notification_id}"

