from django.db import models
from core.models import BaseModel, SoftDeleteModel
from django.conf import settings

class Booking(SoftDeleteModel):
    """
    Booking request for a venue by a club or user.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled'),
    )

    id_label = models.CharField(max_length=20) # e.g., "REQ-8829"
    
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings_requested"
    )
    club = models.ForeignKey(
        'clubs.Club',
        on_delete=models.CASCADE,
        related_name="club_bookings",
        null=True,
        blank=True
    )
    venue = models.ForeignKey(
        'venues.Venue',
        on_delete=models.CASCADE,
        related_name="venue_bookings"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    purpose = models.TextField()
    
    # Requirements
    expected_attendance = models.PositiveIntegerField(default=0)
    equipment_requested = models.JSONField(default=list, blank=True)
    special_requests = models.TextField(blank=True)

    # Scheduling
    requested_date_iso = models.DateTimeField() # e.g., "2024-10-24T00:00:00.000Z"
    time_range = models.CharField(max_length=100) # e.g., "14:00 - 17:30"
    
    # Link to event if booking is approved and creates an event
    event = models.OneToOneField(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="booking"
    )

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['requested_date_iso']),
        ]

    def __str__(self):
        return f"{self.id_label}: {self.venue.name} by {self.requester.name}"
    
    def save(self, *args, **kwargs):
        # Generate ID label if not set - Simple placeholder logic
        if not self.id_label:
            import random
            random_num = random.randint(1000, 9999)
            self.id_label = f"REQ-{random_num}"
        super().save(*args, **kwargs)

