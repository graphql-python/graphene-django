import datetime
import re

import pytest
from django.db.models import Count, Prefetch

from graphene import List, NonNull, ObjectType, Schema, String

from ..fields import DjangoListField
from ..types import DjangoObjectType
from .models import (
    Article as ArticleModel,
    Film as FilmModel,
    FilmDetails as FilmDetailsModel,
    Person as PersonModel,
    Reporter as ReporterModel,
)


class TestDjangoListField:
    def test_only_django_object_types(self):
        class Query(ObjectType):
            something = DjangoListField(String)

        with pytest.raises(TypeError) as excinfo:
            Schema(query=Query)

        assert (
            "Query fields cannot be resolved. DjangoListField only accepts DjangoObjectType types as underlying type"
            in str(excinfo.value)
        )

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

    def test_same_type_nested_list_field(self):
        class Person(DjangoObjectType):
            class Meta:
                model = PersonModel
                fields = ("name", "parent")

            children = DjangoListField(lambda: Person)

        class Query(ObjectType):
            persons = DjangoListField(Person)

        schema = Schema(query=Query)

        query = """
            query {
                persons {
                    name
                    children {
                        name
                    }
                }
            }
        """

        p1 = PersonModel.objects.create(name="Tara")
        PersonModel.objects.create(name="Debra")

        PersonModel.objects.create(
            name="Toto",
            parent=p1,
        )
        PersonModel.objects.create(
            name="Tata",
            parent=p1,
        )

        result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "persons": [
                {
                    "name": "Tara",
                    "children": [
                        {"name": "Toto"},
                        {"name": "Tata"},
                    ],
                },
                {
                    "name": "Debra",
                    "children": [],
                },
                {
                    "name": "Toto",
                    "children": [],
                },
                {
                    "name": "Tata",
                    "children": [],
                },
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

    def test_resolve_list_external_resolver(self):
        """Resolving a plain list from external resolver should work (and not call get_queryset)"""

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

        def resolve_reporters(_, info):
            return [ReporterModel.objects.get(first_name="Debra")]

        class Query(ObjectType):
            reporters = DjangoListField(Reporter, resolver=resolve_reporters)

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

    def test_get_queryset_filter_external_resolver(self):
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

        def resolve_reporters(_, info):
            return ReporterModel.objects.all()

        class Query(ObjectType):
            reporters = DjangoListField(Reporter, resolver=resolve_reporters)

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

    def test_select_related_and_prefetch_related_are_respected(
        self, django_assert_num_queries
    ):
        class Article(DjangoObjectType):
            class Meta:
                model = ArticleModel
                fields = ("headline", "editor", "reporter")

        class Film(DjangoObjectType):
            class Meta:
                model = FilmModel
                fields = ("genre", "details")

        class FilmDetail(DjangoObjectType):
            class Meta:
                model = FilmDetailsModel
                fields = ("location",)

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name", "articles", "films")

        class Query(ObjectType):
            articles = DjangoListField(Article)

            @staticmethod
            def resolve_articles(root, info):
                # Optimize for querying associated editors and reporters, and the films and film
                # details of those reporters. This is similar to what would happen using a library
                # like https://github.com/tfoxy/graphene-django-optimizer for a query like the one
                # below (albeit simplified and hardcoded here).
                return ArticleModel.objects.select_related(
                    "editor", "reporter"
                ).prefetch_related(
                    Prefetch(
                        "reporter__films",
                        queryset=FilmModel.objects.select_related("details"),
                    ),
                )

        schema = Schema(query=Query)

        query = """
            query {
                articles {
                    headline

                    editor {
                        firstName
                    }

                    reporter {
                        firstName

                        films {
                            genre

                            details {
                                location
                            }
                        }
                    }
                }
            }
        """

        r1 = ReporterModel.objects.create(first_name="Tara", last_name="West")
        r2 = ReporterModel.objects.create(first_name="Debra", last_name="Payne")

        ArticleModel.objects.create(
            headline="Amazing news",
            reporter=r1,
            pub_date=datetime.date.today(),
            pub_date_time=datetime.datetime.now(),
            editor=r2,
        )
        ArticleModel.objects.create(
            headline="Not so good news",
            reporter=r2,
            pub_date=datetime.date.today(),
            pub_date_time=datetime.datetime.now(),
            editor=r1,
        )

        film1 = FilmModel.objects.create(genre="ac")
        film2 = FilmModel.objects.create(genre="ot")
        film3 = FilmModel.objects.create(genre="do")
        FilmDetailsModel.objects.create(location="Hollywood", film=film1)
        FilmDetailsModel.objects.create(location="Antarctica", film=film3)
        r1.films.add(film1, film2)
        r2.films.add(film3)

        # We expect 2 queries to be performed based on the above resolver definition: one for all
        # articles joined with the reporters model (for associated editors and reporters), and one
        # for the films prefetch (which includes its `select_related` JOIN logic in its queryset)
        with django_assert_num_queries(2) as captured:
            result = schema.execute(query)

        assert not result.errors
        assert result.data == {
            "articles": [
                {
                    "headline": "Amazing news",
                    "editor": {"firstName": "Debra"},
                    "reporter": {
                        "firstName": "Tara",
                        "films": [
                            {"genre": "AC", "details": {"location": "Hollywood"}},
                            {"genre": "OT", "details": None},
                        ],
                    },
                },
                {
                    "headline": "Not so good news",
                    "editor": {"firstName": "Tara"},
                    "reporter": {
                        "firstName": "Debra",
                        "films": [
                            {"genre": "DO", "details": {"location": "Antarctica"}},
                        ],
                    },
                },
            ]
        }

        assert len(captured.captured_queries) == 2  # Sanity-check

        # First we should have queried for all articles in a single query, joining on the reporters
        # model (for the editors and reporters ForeignKeys)
        assert re.match(
            r'SELECT .* "tests_article" INNER JOIN "tests_reporter"',
            captured.captured_queries[0]["sql"],
        )

        # Then we should have queried for all of the films of all reporters, joined with the film
        # details for each film, using a single query
        assert re.match(
            r'SELECT .* FROM "tests_film" INNER JOIN "tests_film_reporters" .* LEFT OUTER JOIN "tests_filmdetails"',
            captured.captured_queries[1]["sql"],
        )
