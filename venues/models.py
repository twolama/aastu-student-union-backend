from django.db import models
from core.models import BaseModel, SoftDeleteModel

class VenueCategory(BaseModel):
    """
    Categorization for venues (e.g., Auditorium, Meeting Room).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = 'Venue Category'
        verbose_name_plural = 'Venue Categories'

    def __str__(self):
        return self.name

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
    category = models.ForeignKey(
        VenueCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="venues"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Capacity
    max_capacity = models.PositiveIntegerField(default=0)
    capacity_label = models.CharField(max_length=100, blank=True, help_text="e.g., '1,200 Seats'")
    
    # Location Details
    campus_block = models.CharField(max_length=100, blank=True)
    floor_level = models.CharField(max_length=100, blank=True)
    nearby_landmarks = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True) # Kept for backward compatibility or general address
    
    # Descriptions
    short_description = models.TextField(blank=True, help_text="A brief summary for card previews.")
    full_description = models.TextField(blank=True, help_text="Detailed information, rules, and specifics.")
    
    # Public Availability
    is_publicly_available = models.BooleanField(default=True, help_text="Allow venue to be booked in the student portal.")

    # Media
    hero_image = models.ImageField(upload_to='venues/hero/', null=True, blank=True)
    thumbnail = models.ImageField(upload_to='venues/thumbs/', null=True, blank=True)
    image_url = models.URLField(null=True, blank=True) # Kept for migration/legacy
    
    # List of amenities (Audio, Wifi, Projector etc.)
    amenities = models.JSONField(default=list, blank=True)
    
    # Venue Contact (Expanded from generic JSONField)
    manager_name = models.CharField(max_length=255, blank=True)
    manager_phone = models.CharField(max_length=20, blank=True)
    manager_email = models.EmailField(blank=True)
    contact = models.JSONField(default=dict, blank=True) # Kept for backward compatibility

    # Google Maps Integration
    google_maps_url = models.URLField(max_length=500, blank=True)
    map_coordinates = models.JSONField(default=dict, blank=True)

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Venue'
        verbose_name_plural = 'Venues'
        permissions = [
            ('manage_venue', 'Can manage venues'),
            ('manage_venue_gallery', 'Can manage venue gallery images'),
        ]
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.campus_block or self.location})"

class VenueImage(BaseModel):
    """
    Gallery images for a venue.
    """
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="gallery"
    )
    image = models.ImageField(upload_to='venues/gallery/')
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = 'Venue Gallery Image'
        verbose_name_plural = 'Venue Gallery Images'


