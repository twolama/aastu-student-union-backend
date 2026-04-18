from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager, Group
from core.models import SoftDeleteModel, Department

class Role(SoftDeleteModel):
    """
    Dynamic roles for the Student Union.
    Each role can be linked to a Django Group for permission management.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    group = models.OneToOneField(
        Group, 
        on_delete=models.CASCADE, 
        related_name='role_profile',
        blank=True,
        null=True,
        help_text="The Django Group that manages permissions for this role."
    )
    is_staff_role = models.BooleanField(default=False, help_text="Should users with this role have admin panel access?")

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name

class User(SoftDeleteModel, AbstractUser):
    """
    Custom user model following Next.js frontend requirements.
    Supports dynamic roles via the Role model.
    """
    name = models.CharField(max_length=255)
    student_id = models.CharField(max_length=50, unique=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    dorm_block = models.CharField(max_length=20, null=True, blank=True)
    dorm_room = models.CharField(max_length=20, null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True, help_text="Personal biography or office note.")
    
    # We use email as second identity but keep username for legacy/internal auth
    email = models.EmailField(unique=True)

    objects: UserManager = UserManager() # type: ignore

    class Meta(SoftDeleteModel.Meta):
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.name} ({self.student_id})"

    @property
    def initials(self) -> str:
        if not self.name:
            return ""
        parts = self.name.split()
        return "".join([p[0].upper() for p in parts[:2]])

    def save(self, *args, **kwargs):
        """
        Overwrite save to sync role permissions and admin access.
        """
        if self.role:
            # Automatically set is_staff if the role allows it
            if self.role.is_staff_role:
                self.is_staff = True
            
            # Note: Group assignment is normally handled AFTER first save if 
            # using M2M, but since Role has a 1-to-1 to Group, we can 
            # ensure the user is in that group here or via signals.
        
        super().save(*args, **kwargs)

        # After saving, ensure user is in the correct group
        if self.role and self.role.group:
            self.groups.add(self.role.group)

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "No Role"

