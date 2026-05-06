from django.db.models import Q
from uuid import uuid4
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from typing import Any, cast

from core.models import Department

from .models import Role, User


class UserImportResource(resources.ModelResource):
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

    def before_import_row(self, row, **kwargs):
        username = row.get('username')
        student_id = row.get('student_id')
        email = row.get('email')

        if isinstance(username, str):
            username = username.strip()
        if isinstance(student_id, str):
            student_id = student_id.strip()
        if isinstance(email, str):
            email = email.strip()

        # Preserve original input student_id for later matching
        row['_input_student_id'] = student_id

        # Ensure username fallback
        row['username'] = username or student_id or email

        # Only generate and set a placeholder student_id when the CSV left it
        # blank. If the CSV provided a student_id, preserve it so matching can
        # find existing users instead of mutating the value.
        if not student_id:
            chosen_sid = row['username'] or row.get('email')
            if not chosen_sid:
                # generate a short unique token
                chosen_sid = f"import-{uuid4().hex[:10]}"

            # ensure uniqueness by appending a suffix if needed
            base = chosen_sid
            counter = 0
            while User.objects.filter(student_id=chosen_sid).exists():
                counter += 1
                chosen_sid = f"{base}-{counter}"

            row['student_id'] = chosen_sid
        row['email'] = email

        if row.get('is_active') in (None, ''):
            row['is_active'] = True

    def get_instance(self, instance_loader, row):
        # Use the original input student_id when attempting to detect existing
        # users. This lets us match existing blank/empty student_id rows if the
        # CSV left the student_id empty.
        input_sid = (row.get('_input_student_id') if '_input_student_id' in row else None)
        input_sid = (input_sid or '').strip()

        student_id = (row.get('student_id') or '').strip()
        email = (row.get('email') or '').strip()
        username = (row.get('username') or '').strip()

        query = Q()
        # If the original input had an empty student_id, consider matching
        # existing users whose student_id is empty as well.
        if input_sid == '':
            query |= Q(student_id='')
        if student_id:
            query |= Q(student_id=student_id)
        if email:
            query |= Q(email__iexact=email)
        if username:
            query |= Q(username=username)

        if not query:
            return None

        return User.objects.filter(query).first()

    def after_init_instance(self, instance, new, row, **kwargs):
        instance._import_was_existing = not new

    def skip_row(self, instance, original, row, import_validation_errors=None):
        return getattr(instance, '_import_was_existing', False)

    def before_save_instance(self, instance, row, **kwargs):
        instance.set_unusable_password()
