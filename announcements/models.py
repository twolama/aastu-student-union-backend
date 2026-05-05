from django.db import models
from core.models import BaseModel, SoftDeleteModel
from django.conf import settings

class AnnouncementCategory(SoftDeleteModel):
    """
    Dynamic category for announcements (e.g., Academic, Social, Union).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Announcement Category'
        verbose_name_plural = 'Announcement Categories'

    def __str__(self):
        return self.name

class Announcement(SoftDeleteModel):
    """
    Official news or announcement published on the portal.
    """
    title = models.CharField(max_length=255)
    category = models.ForeignKey(
        AnnouncementCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements"
    )
    is_pinned = models.BooleanField(default=False, help_text="Pin to top of the list")
    is_published = models.BooleanField(default=False, help_text="Whether the announcement is published and visible to the public")
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements_authored"
    )
    author_name = models.CharField(max_length=255, blank=True) # Preserving name as fallback or explicit label
    
    image = models.ImageField(upload_to='announcements/', null=True, blank=True)
    
    # Simple list of searchable tags
    tags = models.JSONField(default=list, blank=True)
    
    # Store main body as rich text (HTML)
    body = models.TextField(help_text="Rich text content (HTML)")
    
    # Optional field for instruction steps (can also be merged into rich text body)
    procedure_steps = models.JSONField(default=list, blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return self.title

