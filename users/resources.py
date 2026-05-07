from django.db.models import Q
from uuid import uuid4
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from typing import Any, cast
import secrets
import threading
import logging
from django.db import transaction
from django.utils import timezone

from core.models import Department

from .models import Role, User
from .views import _send_user_invitation_email

logger = logging.getLogger(__name__)


class UserImportResource(resources.ModelResource):
    """
    Custom resource for importing users with automatic email invitation for newly created accounts.
    """
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=ForeignKeyWidget(cast(Any, Department), field='name'),
    )
    roles = fields.Field(
        column_name='roles',
        attribute='roles',
        widget=ManyToManyWidget(cast(Any, Role), field='slug'),
    )

    class Meta:
        model = User
        fields = (
            'username',
            'name',
            'student_id',
            'email',
            'phone_number',
            'department',
            'roles',
            'dorm_block',
            'dorm_room',
            'bio',
            'is_active',
        )
        export_order = (
            'username',
            'name',
            'student_id',
            'email',
            'phone_number',
            'department',
            'roles',
            'dorm_block',
            'dorm_room',
            'bio',
            'is_active',
        )
        skip_unchanged = False
        report_skipped = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track newly created users for email sending
        self._new_users_for_email = []

    def before_import_row(self, row, **kwargs):
        # Normalize row keys to handle headers with leading/trailing whitespace
        # This is common in CSVs and can cause fields to be missed.
        normalized_data = {str(k).strip(): v for k, v in row.items() if k is not None}
        row.update(normalized_data)

        username = row.get('username')
        student_id = row.get('student_id')
        email = row.get('email')
        phone_number = row.get('phone_number')

        if isinstance(username, str):
            username = username.strip()
        if isinstance(student_id, str):
            student_id = student_id.strip()
        if isinstance(email, str):
            email = email.strip()
        
        # Handle scientific notation in phone numbers (common Excel issue)
        if phone_number:
            phone_str = str(phone_number).strip()
            if 'E+' in phone_str.upper():
                try:
                    # Convert scientific notation (e.g., 2.52E+11) to integer string
                    phone_str = str(int(float(phone_str)))
                except (ValueError, TypeError):
                    pass
            row['phone_number'] = phone_str

        # Preserve original input for matching, but ensure we have values
        row['_input_student_id'] = student_id
        row['_input_email'] = email
        row['_input_username'] = username

        # Fallback for username if missing
        if not username:
            row['username'] = student_id or email

        # Handle missing student_id for new users only in after_init_instance or before_save
        # To keep the preview accurate, we don't generate the placeholder here anymore
        # unless it's absolutely necessary for get_instance (which it isn't if we match by email/user).

        if row.get('is_active') in (None, ''):
            row['is_active'] = True

        # Sanitize roles field
        roles_raw = row.get('roles')
        if isinstance(roles_raw, str):
            roles_clean = roles_raw.strip()
            # If roles contains an email-like value or a suspicious long
            # numeric token, clear it to avoid accidental assignment.
            if ('@' in roles_clean) or (roles_clean.replace(',', '').replace(' ', '').isdigit() and len(roles_clean) > 10):
                logger.warning(
                    f"Sanitizing suspicious roles value for import row: {roles_raw}",
                    extra={"row": dict(row)},
                )
                row['roles'] = ''
            else:
                row['roles'] = roles_clean
    def get_instance(self, instance_loader, row):
        # We only want to match by fields that are actually provided in the CSV.
        # Matching by empty strings (like blank student_id) can lead to accidental 
        # merging with existing users (like super-admins) who also have blank student_ids.
        
        student_id = (row.get('student_id') or '').strip()
        email = (row.get('email') or '').strip()
        username = (row.get('username') or '').strip()

        # If everything is empty, we can't match anything
        if not any([student_id, email, username]):
            return None

        # Build query only with non-empty fields using OR logic
        query = Q()
        if student_id:
            query |= Q(student_id=student_id)
        if email:
            query |= Q(email__iexact=email)
        if username:
            query |= Q(username=username)

        # Helpful debug: log the incoming matching fields
        logger.debug(
            "Import matching fields: student_id=%s email=%s username=%s",
            student_id,
            email,
            username,
        )

        # Search for existing user
        instance = User.objects.filter(query).first()
        
        # PROTECTION: Never match with a superuser to avoid accidental merging/overwriting
        # of the main admin account data.
        if instance and instance.is_superuser:
            logger.warning(
                f"Import row for {username or email} matched existing superuser. "
                "Ignoring match to prevent accidental merging with admin account."
            )
            return None

        if instance:
            logger.info(
                f"Matched existing user: {instance.username} (ID: {instance.pk}) "
                f"for row with username: {username}, email: {email}"
            )
            
        return instance

    def after_init_instance(self, instance, new, row, **kwargs):
        """
        Mark whether this instance is new or existing.
        For new instances, generate a temporary password and set default roles.
        """
        instance._import_was_existing = not new
        
        if new:
            # Generate temporary password for new users
            instance._import_temp_password = secrets.token_urlsafe(9)
            
            # Set default role in row if missing, so ManyToManyWidget can process it
            roles_raw = row.get('roles')
            if not roles_raw or not str(roles_raw).strip():
                row['roles'] = 'member'
                logger.info(f"Set default 'member' role in row for new user: {row.get('username') or row.get('email')}")

            logger.info(
                f"Initializing new user in import: {instance.email or instance.username}",
                extra={"email": instance.email, "username": instance.username},
            )
        else:
            instance._import_temp_password = None

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Skip existing users from being updated during import.
        """
        # Use presence of `original` (preexisting DB instance) as the
        # canonical indicator that this row corresponds to an existing user.
        is_existing = original is not None
        if is_existing:
            email = getattr(original, 'email', getattr(instance, 'email', None))
            user_id = str(getattr(original, 'pk', getattr(instance, 'pk', None)))
            logger.info(
                f"Skipping existing user: {email}",
                extra={"email": email, "user_id": user_id},
            )
    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Determine if this row should be skipped.
        We now allow updating existing users (except superusers) to give better feedback in the UI.
        """
        if original is None:
            return False
            
        # ALWAYS skip superusers if they were somehow matched (backup check)
        if getattr(original, 'is_superuser', False):
            logger.info(f"Skipping row because it matched superuser: {original.email}")
            return True

        # For other existing users, we return False to allow an "Update" instead of "Skip".
        # This allows the admin to see WHICH users already exist in the preview.
        # If they don't want to update, they can see the "Update" status and cancel.
        return False

    def before_save_instance(self, instance, row, **kwargs):
        """
        Ensure required fields are set and track new users for email sending.
        """
        if getattr(instance, '_import_was_existing', False):
            # For existing users, we allow the update but don't change password
            logger.info(f"Updating existing user: {instance.email}")
            return
        
        # NEW USER LOGIC
        # 1. Ensure student_id is set (cannot be empty due to unique constraint)
        if not instance.student_id:
            # Generate a fallback student_id if missing in CSV
            # Use username or email as base, otherwise random token
            fallback = instance.username or instance.email or f"id-{uuid4().hex[:8]}"
            
            # Ensure uniqueness in database
            candidate = fallback
            counter = 0
            while User.objects.filter(student_id=candidate).exists():
                counter += 1
                candidate = f"{fallback}-{counter}"
            
            instance.student_id = candidate
            logger.info(f"Generated student_id for new user: {instance.student_id}")

        # 2. Ensure username is set (AbstractUser requirement)
        if not instance.username:
            instance.username = instance.student_id or instance.email
        
        # 3. Set unusable password initially
        instance.set_unusable_password()
        
        # Mark that this user needs password and email setup
        instance._setup_invitation = True

    def after_save_instance(self, instance, row, **kwargs):
        """
        After a user is saved, set up password and track for email sending (new users only).
        """
        # Only process new users
        if getattr(instance, '_import_was_existing', False):
            return
        
        # NOTE: Default role 'member' is now handled by modifying the 'row' 
        # in after_init_instance, allowing ManyToManyWidget to handle it naturally.

        # 2. Set temporary password and track for email invitation
        temp_password = getattr(instance, '_import_temp_password', None)
        if temp_password:
            instance.set_password(temp_password)
            instance.must_change_password = True
            instance.save(update_fields=['password', 'must_change_password'])
            
            logger.info(
                f"Set temporary password and tracking for email: {instance.email}",
                extra={"email": instance.email, "user_id": str(instance.pk)},
            )
            
            # Track for email sending
            self._new_users_for_email.append({
                'user_id': str(instance.pk),
                'email': instance.email,
                'name': instance.name,
                'temp_password': temp_password,
            })

    def import_data(
        self,
        dataset,
        dry_run=False,
        raise_errors=False,
        use_transactions=None,
        collect_failed_rows=False,
        rollback_on_validation_errors=False,
        **kwargs,
    ):
        """
        Override import_data to send invitation emails after successful import.
        Emails are queued and sent asynchronously in background daemon threads
        so the import returns immediately and sending does not block.
        """
        # Reset tracking list for this import run
        self._new_users_for_email = []

        # Call parent import with the original signature parameters
        result = super().import_data(
            dataset,
            dry_run=dry_run,
            raise_errors=raise_errors,
            use_transactions=use_transactions,
            collect_failed_rows=collect_failed_rows,
            rollback_on_validation_errors=rollback_on_validation_errors,
            **kwargs,
        )

        # If this was not a dry run, queue invitation emails for newly created users
        if not dry_run and self._new_users_for_email:
            self._send_invitation_emails_for_imported_users()

        return result

    def _send_invitation_emails_for_imported_users(self) -> None:
        """
        Send invitation emails for all newly imported users.
        Uses daemon threads for true fire-and-forget behavior - returns immediately.
        """
        if not self._new_users_for_email:
            return
        
        logger.info(
            f"Queuing invitation emails for {len(self._new_users_for_email)} imported users (async)"
        )
        
        def dispatch_emails():
            """Send emails in background - doesn't block import completion."""
            for user_data in self._new_users_for_email:
                try:
                    logger.info(
                        f"Sending invitation email for imported user: {user_data['email']}",
                        extra={"email": user_data['email']},
                    )
                    _send_user_invitation_email(
                        user_data['user_id'],
                        user_data['email'],
                        user_data['name'],
                        user_data['temp_password'],
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send email for imported user {user_data['email']}: {str(e)}",
                        extra={"email": user_data['email']},
                        exc_info=True,
                    )
        
        # Start daemon thread for true fire-and-forget behavior
        # Daemon threads don't block process exit or import completion
        thread = threading.Thread(
            target=dispatch_emails,
            daemon=True,  # Fire-and-forget: returns immediately, doesn't wait
            name="import-user-emails-bg",
        )
        thread.start()
