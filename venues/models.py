from django.db import models
from core.models import BaseModel, SoftDeleteModel

class Venue(SoftDeleteModel):
    """
    Physical venue or space on campus.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('maintenance', 'Maintenance'),
        ('inactive', 'Inactive'),
    )

    name = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    type_label = models.CharField(max_length=100) # e.g., "Auditorium", "Lab"
    capacity_label = models.CharField(max_length=100) # e.g., "1,200 Seats"
    location = models.CharField(max_length=255) # e.g., "Block 5, 2nd Floor"
    image_url = models.URLField(null=True, blank=True)
    
    # List of amenities (Audio, Wifi, Projector etc.)
    amenities = models.JSONField(default=list)
    
    # Store contact details (name, role, phone, email)
    contact = models.JSONField(default=dict)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Venue'
        verbose_name_plural = 'Venues'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.location})"

