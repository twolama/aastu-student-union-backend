from django.db import models
from django.utils import timezone
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
    short_description = models.TextField() # Renamed from summary
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_mega_event = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False) # Frontend explicit flag
    max_capacity = models.BigIntegerField(default=0) # Changed to BigIntegerField to support large capacity numbers
    
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="associated_events"
    )
    
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
    physical_location_details = models.TextField(blank=True, help_text="e.g. Block 45, Second floor, Room 204")
    
    cover_image = models.ImageField(upload_to='events/covers/', null=True, blank=True)
    
    # Scheduling
    start_date_time = models.DateTimeField(null=True, blank=True)
    end_date_time = models.DateTimeField(null=True, blank=True)
    
    registration_link = models.URLField(blank=True, null=True)
    
    # Store description as rich text (HTML)
    description = models.TextField(help_text="Rich text content (HTML)")
    
    # Store attendance details (current, capacity, waitlist, vips)
    attendance = models.JSONField(default=dict, blank=True)
    
    # Store logistics/schedule points
    logistics = models.JSONField(default=list, blank=True, help_text="List of EventLogisticsPoint")
    
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
            models.Index(fields=['start_date_time']),
        ]

    def __str__(self):
        return f"{self.title} by {self.organizing_club.name}"

    def get_effective_status(self):
        """
        Derive the current event status from its schedule, allowing manual overrides.
        """
        if self.is_archived:
            return "archived"

        # Allow manual override only for live-now. 
        # Manual archiving should use the is_archived flag.
        if self.status == "live-now":
            return "live-now"

        now = timezone.now()
        start = self.start_date_time
        end = self.end_date_time

        if start and now < start:
            return "upcoming"

        if end and now >= end:
            return "archived"

        if start and (end is None or now >= start):
            return "live-now"

        if end and now < end:
            return "live-now"

        return self.status if self.status else "upcoming"

    def save(self, *args, **kwargs):
        """
        Preserve the user-selected status from API/forms.
        """
        super().save(*args, **kwargs)

class EventVolunteer(SoftDeleteModel):
    """
    Volunteers assigned to specific events, linked to platform users.
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="volunteers"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Changed from CASCADE to keep record if user deleted
        related_name="event_volunteering",
        null=True,
        blank=True,
        help_text="The registered user volunteering for this event."
    )
    # Manual entry fields to match frontend
    full_name = models.CharField(max_length=255, blank=True)
    student_id = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=100, blank=True, help_text="e.g. Usher, Coordinator")

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Event Volunteer'
        verbose_name_plural = 'Event Volunteers'

    def __str__(self):
        user_name = self.user.name if self.user else self.full_name
        return f"{user_name} - {self.role} for {self.event.title}"

