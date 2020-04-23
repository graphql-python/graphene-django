import datetime

import pytest

from graphene import List, NonNull, ObjectType, Schema, String
from mock import mock
from unittest import TestCase
from django.core.exceptions import PermissionDenied
from graphene_django.fields import DjangoField, DataLoaderField
from promise.dataloader import DataLoader
from promise import Promise
from ..fields import DjangoListField
from ..types import DjangoObjectType
from .models import Article as ArticleModel
from .models import Reporter as ReporterModel


@pytest.mark.django_db
class TestDjangoListField:
    def test_only_django_object_types(self):
        class TestType(ObjectType):
            foo = String()

        with pytest.raises(AssertionError):
            list_field = DjangoListField(TestType)

    def test_only_import_paths(self):
        list_field = DjangoListField("graphene_django.tests.schema.Human")
        from .schema import Human

        assert list_field._type.of_type.of_type is Human

    def test_non_null_type(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        list_field = DjangoListField(NonNull(Reporter))

        assert isinstance(list_field.type, List)
        assert isinstance(list_field.type.of_type, NonNull)
        assert list_field.type.of_type.of_type is Reporter

    def test_get_django_model(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        list_field = DjangoListField(Reporter)
        assert list_field.model is ReporterModel

    def test_list_field_default_queryset(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
                }
            }
        """

        ReporterModel.objects.create(first_name="Tara", last_name="West")
        ReporterModel.objects.create(first_name="Debra", last_name="Payne")

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "reporters": [{"firstName": "Tara"}, {"firstName": "Debra"}]
        }

    def test_override_resolver(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

            def resolve_reporters(_, info):
                return ReporterModel.objects.filter(first_name="Tara")

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
                }
            }
        """

        ReporterModel.objects.create(first_name="Tara", last_name="West")
        ReporterModel.objects.create(first_name="Debra", last_name="Payne")

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {"reporters": [{"firstName": "Tara"}]}

    def test_nested_list_field(self):
        class Article(DjangoObjectType):
            class Meta:
                model = ArticleModel
                fields = ("headline",)

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name", "articles")

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
                    articles {
                        headline
                    }
                }
            }
        """

        r1 = ReporterModel.objects.create(first_name="Tara", last_name="West")
        ReporterModel.objects.create(first_name="Debra", last_name="Payne")

        ArticleModel.objects.create(
            headline="Amazing news",
            reporter=r1,
            pub_date=datetime.date.today(),
            pub_date_time=datetime.datetime.now(),
            editor=r1,
        )

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "reporters": [
                {"firstName": "Tara", "articles": [{"headline": "Amazing news"}]},
                {"firstName": "Debra", "articles": []},
            ]
        }

    def test_override_resolver_nested_list_field(self):
        class Article(DjangoObjectType):
            class Meta:
                model = ArticleModel
                fields = ("headline",)

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name", "articles")

            def resolve_reporters(reporter, info):
                return reporter.articles.all()

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
                    articles {
                        headline
                    }
                }
            }
        """

        r1 = ReporterModel.objects.create(first_name="Tara", last_name="West")
        ReporterModel.objects.create(first_name="Debra", last_name="Payne")

        ArticleModel.objects.create(
            headline="Amazing news",
            reporter=r1,
            pub_date=datetime.date.today(),
            pub_date_time=datetime.datetime.now(),
            editor=r1,
        )

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "reporters": [
                {"firstName": "Tara", "articles": [{"headline": "Amazing news"}]},
                {"firstName": "Debra", "articles": []},
            ]
        }


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
        field = DjangoField(MyType, permissions=["perm1", "perm2"], source="resolver")
        resolver = field.get_resolver(None)

        class Viewer(object):
            def has_perm(self, perm):
                return perm == "perm2"

        info = mock.Mock(context=mock.Mock(user=Viewer()))

        self.assertEqual(resolver(MyInstance(), info), MyInstance().resolver())

    def test_permission_field_without_permission(self):
        MyType = object()
        field = DjangoField(MyType, permissions=["perm1", "perm2"], source="resolver")
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
        data_loader_field = DataLoaderField(
            data_loader=data_loader, source_loader="key", type=MyType
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.key)

    def test_dataloaderfield_many(self):
        MyType = object()
        data_loader_field = DataLoaderField(
            data_loader=data_loader, source_loader="keys", type=MyType, load_many=True
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.keys)

    def test_dataloaderfield_inner_prop(self):
        MyType = object()
        data_loader_field = DataLoaderField(
            data_loader=data_loader, source_loader="InnerClass.key", type=MyType
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.InnerClass.key)

    def test_dataloaderfield_many_inner_prop(self):
        MyType = object()
        data_loader_field = DataLoaderField(
            data_loader=data_loader,
            source_loader="InnerClass.keys",
            type=MyType,
            load_many=True,
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        self.assertEqual(resolver(instance, None).get(), instance.InnerClass.keys)

    def test_dataloaderfield_permissions(self):
        MyType = object()
        data_loader_field = DataLoaderField(
            data_loader=data_loader,
            source_loader="key",
            type=MyType,
            permissions=["perm1", "perm2"],
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        class Viewer(object):
            def has_perm(self, perm):
                return perm == "perm2"

        info = mock.Mock(context=mock.Mock(user=Viewer()))

        self.assertEqual(resolver(instance, info).get(), instance.key)

    def test_dataloaderfield_without_permissions(self):
        MyType = object()
        data_loader_field = DataLoaderField(
            data_loader=data_loader,
            source_loader="key",
            type=MyType,
            permissions=["perm1", "perm2"],
        )

        resolver = data_loader_field.get_resolver(None)
        instance = MyInstance()

        class Viewer(object):
            def has_perm(self, perm):
                return False

        info = mock.Mock(context=mock.Mock(user=Viewer()))
        with self.assertRaises(PermissionDenied):
            resolver(instance, info)
