from django.db import models
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

