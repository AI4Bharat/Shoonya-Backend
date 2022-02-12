from django.test import TestCase
from .models import User


class UserTest(TestCase):

    def setUp(self):
        User.objects.create(username='test', email='test@gmail.com')
        User.objects.create(username='test2', email='test2@gmai.com', first_name='test', last_name='2', role=2)

    def test_name_or_email(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.name_or_email(), "test@gmail.com"
        )
        self.assertEqual(
            user_two.name_or_email(), "test 2"
        )
    
    def test_get_full_name(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.get_full_name(), ''
        )
        self.assertEqual(
            user_two.get_full_name(), 'test 2'
        )

    def test_get_short_name(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.get_short_name(), ''
        )
        self.assertEqual(
            user_two.get_short_name(), 'test'
        )

    def test_is_annotator(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.is_annotator(), True
        )
        self.assertEqual(
            user_two.is_annotator(), False
        )

    def test_is_workspace_manager(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.is_workspace_manager(), False
        )
        self.assertEqual(
            user_two.is_workspace_manager(), True
        )

    def test_is_organization_owner(self):
        user_one=User.objects.get(username='test')
        user_two=User.objects.get(username='test2')
        self.assertEqual(
            user_one.is_organization_owner(), False
        )
        self.assertEqual(
            user_two.is_organization_owner(), False
        )

