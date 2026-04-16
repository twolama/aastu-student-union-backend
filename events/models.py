from django.db import models
from core.models import BaseModel, SoftDeleteModel
from django.conf import settings

class Event(SoftDeleteModel):
    """
    Campus event organized by a club at a venue.
    """
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming Event'),
        ('live-now', 'Happening Now'),
        ('archived', 'Past Event'),
    )

    title = models.CharField(max_length=255)
    summary = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_mega_event = models.BooleanField(default=False)
    
    organizing_club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name="organized_events"
    )
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_events"
    )
    
    cover_image_url = models.URLField(null=True, blank=True)
    
    # Scheduling
    schedule_date = models.DateField()
    schedule_time_range = models.CharField(max_length=100) # e.g., "09:00 AM - 05:00 PM"
    
    # Store about sections as paragraphs in JSON
    about_paragraphs = models.JSONField(default=list)
    
    # Store attendance details (current, capacity, waitlist, vips)
    attendance = models.JSONField(default=dict)
    
    # Track registered users (ManyToManyField)
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="attended_events"
    )

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['schedule_date']),
        ]

    def __str__(self):
        return f"{self.title} by {self.organizing_club.name}"

