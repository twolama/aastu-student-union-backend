from django.db import models
from core.models import BaseModel, SoftDeleteModel
from django.conf import settings

class Announcement(SoftDeleteModel):
    """
    Official news or announcement published on the portal.
    """
    CATEGORY_CHOICES = (
        ('academic', 'Academic Updates'),
        ('social', 'Social Events'),
        ('union', 'Student Union News'),
    )

    title = models.CharField(max_length=255)
    summary = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='union')
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcements_authored"
    )
    author_name = models.CharField(max_length=255) # Preserving name as fallback or explicit label
    
    image = models.ImageField(upload_to='announcements/', null=True, blank=True)
    
    # Simple list of searchable tags
    tags = models.JSONField(default=list)
    
    # Store procedure steps if this announcement provides instructions
    procedure_steps = models.JSONField(default=list)
    
    # Store additional content paragraphs
    content_paragraphs = models.JSONField(default=list)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.title

