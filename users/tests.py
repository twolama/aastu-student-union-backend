from django.contrib.auth.models import Group
from django.test import TestCase
from tablib import Dataset

from core.models import College, Department

from .models import Role, User
from .resources import UserImportResource


class UserImportResourceTests(TestCase):
	def setUp(self):
		self.college = College.objects.create(
			name='College of Engineering',
			abbreviation='COE',
			description='Engineering college',
		)
		self.department = Department.objects.create(
			name='Software Engineering',
			slug='software-engineering',
			college=self.college,
		)
		self.member_role = Role.objects.create(
			name='Member',
			slug='member',
			description='General member',
			is_staff_role=False,
		)
		self.staff_group = Group.objects.create(name='Import Staff Group')
		self.staff_role = Role.objects.create(
			name='Admin Member',
			slug='admin-member',
			description='Staff-access role',
			is_staff_role=True,
		)
		self.staff_role.groups.add(self.staff_group)
		self.existing_user = User.objects.create_user(
			username='existing-user',
			name='Existing User',
			student_id='STU-0001',
			email='existing@aastu.edu.et',
			department=self.department,
			is_active=True,
		)

	def build_dataset(self):
		dataset = Dataset()
		dataset.headers = [
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
		]
		dataset.append([
			'',
			'New Import User',
			'STU-0002',
			'new@aastu.edu.et',
			'0911111111',
			'Software Engineering',
			'member,admin-member',
			'B',
			'204',
			'Imported through admin',
			True,
		])
		dataset.append([
			'',
			'Duplicate User',
			'STU-0001',
			'duplicate@aastu.edu.et',
			'0922222222',
			'Software Engineering',
			'member',
			'C',
			'301',
			'Should be skipped',
			True,
		])
		return dataset

	def test_import_creates_new_users_skips_duplicates_and_sets_unusable_password(self):
		resource = UserImportResource()
		result = resource.import_data(self.build_dataset(), dry_run=False, raise_errors=True)

		self.assertEqual(result.totals['new'], 1)
		self.assertEqual(result.totals['skip'], 1)
		self.assertEqual(User.objects.count(), 2)

		imported_user = User.objects.get(student_id='STU-0002')
		self.assertFalse(imported_user.has_usable_password())
		self.assertEqual(imported_user.username, 'STU-0002')
		self.assertTrue(imported_user.roles.filter(slug='member').exists())
		self.assertTrue(imported_user.roles.filter(slug='admin-member').exists())
		self.assertTrue(imported_user.is_staff)
		self.assertTrue(imported_user.groups.filter(name='Import Staff Group').exists())

		duplicate_user = User.objects.get(student_id='STU-0001')
		self.assertEqual(duplicate_user.email, 'existing@aastu.edu.et')
		self.assertNotEqual(duplicate_user.name, 'Duplicate User')

