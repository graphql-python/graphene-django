import datetime
from django.db.models import Count

import pytest

from graphene import List, NonNull, ObjectType, Schema, String

from ..fields import DjangoListField
from ..types import DjangoObjectType
from .models import Article as ArticleModel
from .models import Reporter as ReporterModel


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

    def test_list_field_queryset_is_not_cached(self):
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

        result = schema.execute(query)
        assert not result.errors
        assert result.data == {"reporters": []}

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
        ArticleModel.objects.create(
            headline="Not so good news",
            reporter=r1,
            pub_date=datetime.date.today(),
            pub_date_time=datetime.datetime.now(),
            editor=r1,
        )

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "reporters": [
                {
                    "firstName": "Tara",
                    "articles": [
                        {"headline": "Amazing news"},
                        {"headline": "Not so good news"},
                    ],
                },
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

            def resolve_articles(reporter, info):
                return reporter.articles.filter(headline__contains="Amazing")

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
        ArticleModel.objects.create(
            headline="Not so good news",
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

    def test_get_queryset_filter(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name", "articles")

            @classmethod
            def get_queryset(cls, queryset, info):
                # Only get reporters with at least 1 article
                return queryset.annotate(article_count=Count("articles")).filter(
                    article_count__gt=0
                )

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

            def resolve_reporters(_, info):
                return ReporterModel.objects.all()

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
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
        assert result.data == {"reporters": [{"firstName": "Tara"}]}

    def test_resolve_list(self):
        """Resolving a plain list should work (and not call get_queryset)"""

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name", "articles")

            @classmethod
            def get_queryset(cls, queryset, info):
                # Only get reporters with at least 1 article
                return queryset.annotate(article_count=Count("articles")).filter(
                    article_count__gt=0
                )

        class Query(ObjectType):
            reporters = DjangoListField(Reporter)

            def resolve_reporters(_, info):
                return [ReporterModel.objects.get(first_name="Debra")]

        schema = Schema(query=Query)

        query = """
            query {
                reporters {
                    firstName
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
        assert result.data == {"reporters": [{"firstName": "Debra"}]}

    def test_get_queryset_foreign_key(self):
        class Article(DjangoObjectType):
            class Meta:
                model = ArticleModel
                fields = ("headline",)

            @classmethod
            def get_queryset(cls, queryset, info):
                # Rose tinted glasses
                return queryset.exclude(headline__contains="Not so good")

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
        ArticleModel.objects.create(
            headline="Not so good news",
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
