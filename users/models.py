from django.conf import settings
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser, UserManager, Group
from django.contrib.auth.models import Permission
from core.models import SoftDeleteModel, Department


DEFAULT_MEMBER_PERMISSION_CODENAMES = {
    'announcements.view_announcement',
    'clubs.view_club',
    'events.view_event',
    'venues.view_venue',
    'bookings.view_booking',
}

class Role(SoftDeleteModel):
    """
    Dynamic roles for the Student Union.
    Each role can be linked to multiple Django Groups for permission management.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name='role_profiles',
        help_text="The Django Groups that manage permissions for this role."
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
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name="users",
        help_text="The roles assigned to this user."
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True, null=True, help_text="Personal biography or office note.")
    must_change_password = models.BooleanField(default=False)
    
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
        if self.pk and self.roles.filter(is_staff_role=True).exists():
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False

        super().save(*args, **kwargs)

        # After saving, ensure user groups match current role groups.
        if self.pk:
            self._sync_role_groups()

    def _sync_role_groups(self):
        role_groups = Group.objects.filter(role_profiles__users=self).distinct()
        manual_groups = self.groups.exclude(role_profiles__users=self).distinct()
        self.groups.set(manual_groups.union(role_groups))

    def _get_role_permission_codenames(self) -> set[str]:
        cached_permissions = getattr(self, '_cached_role_permission_codenames', None)
        if cached_permissions is not None:
            return cached_permissions

        codenames: set[str] = set()
        prefetched_roles = getattr(self, '_prefetched_objects_cache', {}).get('roles')
        roles = prefetched_roles if prefetched_roles is not None else self.roles.prefetch_related('groups__permissions__content_type').all()

        role_list = list(roles)
        for role in role_list:
            groups_cache = getattr(role, '_prefetched_objects_cache', {})
            role_groups = groups_cache.get('groups')
            if role_groups is None:
                role_groups = role.groups.prefetch_related('permissions__content_type').all()

            for group in role_groups:
                permissions_cache = getattr(group, '_prefetched_objects_cache', {})
                group_permissions = permissions_cache.get('permissions')
                if group_permissions is None:
                    group_permissions = group.permissions.select_related('content_type').all()

                for permission in group_permissions:
                    codenames.add(f'{permission.content_type.app_label}.{permission.codename}')

        if any(role.slug.lower() == 'member' for role in role_list) and not codenames:
            codenames.update(DEFAULT_MEMBER_PERMISSION_CODENAMES)

        self._cached_role_permission_codenames = codenames
        return codenames

    def get_all_permissions(self, obj=None):
        cached_permissions = getattr(self, '_cached_all_permissions', None)
        if cached_permissions is not None and obj is None:
            return cached_permissions

        permissions = set(super().get_all_permissions(obj=obj))
        permissions.update(self._get_role_permission_codenames())
        if obj is None:
            self._cached_all_permissions = permissions
        return permissions

    def get_group_permissions(self, obj=None):
        cached_permissions = getattr(self, '_cached_group_permissions', None)
        if cached_permissions is not None and obj is None:
            return cached_permissions

        permissions = set(super().get_group_permissions(obj=obj))
        permissions.update(self._get_role_permission_codenames())
        if obj is None:
            self._cached_group_permissions = permissions
        return permissions

    @property
    def role(self) -> Role | None:
        return self.roles.first()

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "No Role"


@receiver(m2m_changed, sender=User.roles.through)
def user_roles_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    if not instance.pk:
        return

    def sync_user(user):
        has_staff_role = user.roles.filter(is_staff_role=True).exists()
        new_staff_status = user.is_superuser or has_staff_role
        if user.is_staff != new_staff_status:
            user.is_staff = new_staff_status
            user.save(update_fields=['is_staff'])
        user._sync_role_groups()

    if reverse:
        # Role.users changed
        if pk_set:
            users = User.objects.filter(pk__in=pk_set)
        else:
            users = instance.users.all()
        for user in users:
            sync_user(user)
    else:
        # User.roles changed
        sync_user(instance)


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_otps',
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
        indexes = [
            models.Index(fields=['otp'], name='users_pr_otp_idx'),
            models.Index(fields=['user', 'is_used', 'expires_at'], name='users_pr_user_idx'),
        ]

    def __str__(self) -> str:
        return f"OTP {self.otp} for {self.user.email} (used={self.is_used})"

