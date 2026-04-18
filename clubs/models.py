from django.db import models
from core.models import BaseModel, SoftDeleteModel
from django.conf import settings

class Club(SoftDeleteModel):
    """
    Club model representing student organizations.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('pending', 'Pending Approval'),
        ('rejected', 'Rejected'),
    )

    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    category_label = models.CharField(max_length=100) # e.g., "Technology", "Sports"
    location_label = models.CharField(max_length=255) # e.g., "Main Campus, Block 24"
    logo_label = models.CharField(max_length=10, blank=True) # Usually first letter or small identifier
    cover_image = models.ImageField(upload_to='clubs/covers/', null=True, blank=True)
    logo = models.ImageField(upload_to='clubs/logos/', null=True, blank=True)
    
    # Store description as rich text (HTML)
    description = models.TextField(help_text="Rich text content (HTML)")
    
    president = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clubs_led"
    )
    advisor_name = models.CharField(max_length=255, blank=True)
    
    # Store social/external links (website, externalMembership)
    links = models.JSONField(default=dict)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Club'
        verbose_name_plural = 'Clubs'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

