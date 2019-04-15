from mock import mock
from unittest import TestCase
from django.core.exceptions import PermissionDenied
from graphene_django.fields import DjangoField, DataLoaderField
from promise.dataloader import DataLoader
from promise import Promise


class MyInstance(object):
    value = "value"
    key = 1
    keys = [1, 2, 3]

    class InnerClass(object):
        key = 2
        keys = [4, 5, 6]

    def resolver(self):
        return "resolver method"


def batch_load_fn(keys):
    return Promise.all(keys)


data_loader = DataLoader(batch_load_fn=batch_load_fn)


class PermissionFieldTests(TestCase):

    def test_permission_field(self):
        MyType = object()
        field = DjangoField(MyType, permissions=['perm1', 'perm2'], source='resolver')
        resolver = field.get_resolver(None)

        class Viewer(object):
            def has_perm(self, perm):
                return perm == 'perm2'

        info = mock.Mock(context=mock.Mock(user=Viewer()))

        self.assertEqual(resolver(MyInstance(), info), MyInstance().resolver())

    def test_permission_field_without_permission(self):
        MyType = object()
        field = DjangoField(MyType, permissions=['perm1', 'perm2'], source='resolver')
        resolver = field.get_resolver(field.resolver)

        class Viewer(object):
            def has_perm(self, perm):
                return False

        info = mock.Mock(context=mock.Mock(user=Viewer()))

        with self.assertRaises(PermissionDenied):
            resolver(MyInstance(), info)


class DataLoaderFieldTests(TestCase):

    def test_dataloaderfield(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='key', type=MyType)

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.key)

    def test_dataloaderfield_many(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='keys', type=MyType, load_many=True)

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.keys)

    def test_dataloaderfield_inner_prop(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='InnerClass.key', type=MyType)

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.InnerClass.key)

    def test_dataloaderfield_many_inner_prop(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='InnerClass.keys', type=MyType,
                                            load_many=True)

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.InnerClass.keys)

    def test_dataloaderfield_permissions(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='key', type=MyType,
                                            permissions=['perm1', 'perm2'])

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        class Viewer(object):
            def has_perm(self, perm):
                return perm == 'perm2'

        info = mock.Mock(context=mock.Mock(user=Viewer()))

        self.assertEqual(resolver(instance, info).get(), instance.key)

    def test_dataloaderfield_without_permissions(self):
        MyType = object()
        data_loader_field = DataLoaderField(data_loader=data_loader, source_loader='key', type=MyType,
                                            permissions=['perm1', 'perm2'])

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        class Viewer(object):
            def has_perm(self, perm):
                return False

        info = mock.Mock(context=mock.Mock(user=Viewer()))
        with self.assertRaises(PermissionDenied):
            resolver(instance, info)
