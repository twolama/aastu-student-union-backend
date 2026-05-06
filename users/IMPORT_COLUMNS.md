User import column guide

The admin import accepts CSV/XLSX files with the following columns (order is flexible but names must match):

- username: Optional. If empty, falls back to student_id or email.
- name: Full name of the user (required for display).
- student_id: Unique student identifier. Used as primary match key.
- email: Unique email address. Used as a secondary match key (case-insensitive).
- phone_number: Optional phone number.
- department: Department name (must match an existing Department.name in the system).
- roles: Comma-separated role slugs (e.g., member,admin-member). Roles are matched by slug.
- dorm_block: Optional dorm block.
- dorm_room: Optional dorm room.
- bio: Optional free-text bio.
- is_active: Optional boolean (True/False). Defaults to True when omitted.

Behavior notes:
- Duplicate rows: a row matching an existing user by student_id, email, or username will be skipped (no update).
- Passwords: imported users receive an unusable password and must complete onboarding or reset their password.
- Role-to-group syncing: when roles include staff roles, the user's is_staff and group memberships are synchronized via existing model hooks.
- Department lookup is by exact department name; create the department first if needed.

Template file: users/static/users/user_import_template.csv

If you need an alternative matching strategy (e.g., upsert by email), ask for an enhancement to the import resource.