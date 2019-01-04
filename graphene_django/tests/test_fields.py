from unittest import TestCase
from django.core.exceptions import PermissionDenied
from graphene_django.fields import DjangoPermissionField


class MyInstance(object):
    value = "value"

    def resolver(self):
        return "resolver method"


class PermissionFieldTests(TestCase):

    def test_permission_field(self):
        MyType = object()
        field = DjangoPermissionField(MyType, permissions=['perm1', 'perm2'], source='resolver')
        resolver = field.get_resolver(field.resolver)

        class Viewer(object):
            def has_perm(self, perm):
                return perm == 'perm2'

        class Info(object):
            class Context(object):
                user = Viewer()
            context = Context()

        self.assertEqual(resolver(MyInstance(), Info()), MyInstance().resolver())

    def test_permission_field_without_permission(self):
        MyType = object()
        field = DjangoPermissionField(MyType, permissions=['perm1', 'perm2'], source='resolver')
        resolver = field.get_resolver(field.resolver)

        class Viewer(object):
            def has_perm(self, perm):
                return False

        class Info(object):
            class Context(object):
                user = Viewer()
            context = Context()

        with self.assertRaises(PermissionDenied):
            resolver(MyInstance(), Info())
