# encoding: utf-8
from django.utils.unittest import TestCase
from ..decorators import has_perms


class MockContext(object):
    def __init__(self, authenticated=True, is_staff=False, superuser=False, perms=[]):
        self.user = self
        self.authenticated = authenticated
        self.is_staff = is_staff
        self.is_superuser = superuser
        self.perms = perms
        self.status_code = 200

    def is_authenticated(self):
        return self.authenticated

    def has_perms(self, check_perms):
        for perm in check_perms:
            if perm not in self.perms:
                return False
        return True


class TestHasPermsDecorator(TestCase):

    @classmethod
    @has_perms(['django_app.dummy_permission'])
    def check_user_perms_func(cls, input, context, info=None):
        cls.status_code = 200
        cls.content = True
        return cls

    def test_get_content_without_permission(self):
        context = MockContext(
            authenticated=True
        )
        request = TestHasPermsDecorator.check_user_perms_func(None, context=context)
        self.assertEqual(request.status_code, 403)
        self.assertEqual(request.content, 'Forbidden. User without access')

    def test_get_content_without_authentication(self):
        context = MockContext(
            authenticated=False
        )
        request = TestHasPermsDecorator.check_user_perms_func(None, context=context)
        self.assertEqual(request.status_code, 403)
        self.assertEqual(request.content, 'Forbidden. User is not authenticated.')

    def test_get_context_with_permission(self):
        context = MockContext(
            authenticated=True,
            perms=['django_app.dummy_permission']

        )
        request = TestHasPermsDecorator.check_user_perms_func(None, context=context)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.content, True)

    def test_get_context_with_diffent_and_valid_permission(self):
        context = MockContext(
            authenticated=True,
            perms=['another_app.dummy_permission',
                   'django_app.dummy_permission']

        )
        request = TestHasPermsDecorator.check_user_perms_func(None, context=context)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.content, True)

    def test_get_context_with_diffent_and_invalid_permission(self):
        context = MockContext(
            authenticated=True,
            perms=['another_app.dummy_permission',
                   'another_app.dummy_permission2']

        )
        request = TestHasPermsDecorator.check_user_perms_func(None, context=context)
        self.assertEqual(request.status_code, 403)
        self.assertEqual(request.content, 'Forbidden. User without access')
