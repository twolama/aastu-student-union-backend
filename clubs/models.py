from django.db import models
from core.models import BaseModel, SoftDeleteModel, Department
from django.conf import settings

class ClubCategory(SoftDeleteModel):
    """
    Dynamic category for student clubs (e.g., Technology, Sports, Arts).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Club Category'
        verbose_name_plural = 'Club Categories'

    def __str__(self):
        return self.name

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
    category = models.ForeignKey(
        ClubCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clubs"
    )
    location_label = models.CharField(max_length=255) # e.g., "Main Campus, Block 24"
    logo_label = models.CharField(max_length=10, blank=True) # Usually first letter or small identifier
    cover_image = models.ImageField(upload_to='clubs/covers/', null=True, blank=True)
    logo = models.ImageField(upload_to='clubs/logos/', null=True, blank=True)
    
    # Store description as rich text (HTML)
    description = models.TextField(help_text="Rich text content (HTML)")
    
    # President/Lead Info (Linked to User)
    president = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clubs_led",
        help_text="The registered User who leads this club. Contact info is pulled from their profile."
    )

    # Advisor Info (Linked to User)
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clubs_advised",
        help_text="The registered User who advises this club."
    )
    
    # Store social/external links (website, externalMembership)
    links = models.JSONField(default=dict, blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Club'
        verbose_name_plural = 'Clubs'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name

