import pytest
from graphql_relay import to_global_id

import graphene
from graphene.relay import Node

from ..types import DjangoObjectType
from .models import Article, Film, FilmDetails, Reporter


class TestShouldCallGetQuerySetOnForeignKey:
    """
    Check that the get_queryset method is called in both forward and reversed direction
    of a foreignkey on types.
    (see issue #1111)

    NOTE: For now, we do not expect this get_queryset method to be called for nested
    objects, as the original attempt to do so prevented SQL query-optimization with
    `select_related`/`prefetch_related` and caused N+1 queries. See discussions here
    https://github.com/graphql-python/graphene-django/pull/1315/files#r1015659857
    and here https://github.com/graphql-python/graphene-django/pull/1401.
    """

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter
                fields = "__all__"

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("admin"):
                    return queryset
                raise Exception("Not authorized to access reporters.")

        class ArticleType(DjangoObjectType):
            class Meta:
                model = Article
                fields = "__all__"

            @classmethod
            def get_queryset(cls, queryset, info):
                return queryset.exclude(headline__startswith="Draft")

        class Query(graphene.ObjectType):
            reporter = graphene.Field(ReporterType, id=graphene.ID(required=True))
            article = graphene.Field(ArticleType, id=graphene.ID(required=True))

            def resolve_reporter(self, info, id):
                return (
                    ReporterType.get_queryset(Reporter.objects, info)
                    .filter(id=id)
                    .last()
                )

            def resolve_article(self, info, id):
                return (
                    ArticleType.get_queryset(Article.objects, info).filter(id=id).last()
                )

        self.schema = graphene.Schema(query=Query)

        self.reporter = Reporter.objects.create(first_name="Jane", last_name="Doe")

        self.articles = [
            Article.objects.create(
                headline="A fantastic article",
                reporter=self.reporter,
                editor=self.reporter,
            ),
            Article.objects.create(
                headline="Draft: My next best seller",
                reporter=self.reporter,
                editor=self.reporter,
            ),
        ]

    def test_get_queryset_called_on_field(self):
        # If a user tries to access an article it is fine as long as it's not a draft one
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                }
            }
        """
        # Non-draft
        result = self.schema.execute(query, variables={"id": self.articles[0].id})
        assert not result.errors
        assert result.data["article"] == {
            "headline": "A fantastic article",
        }
        # Draft
        result = self.schema.execute(query, variables={"id": self.articles[1].id})
        assert not result.errors
        assert result.data["article"] is None

        # If a non admin user tries to access a reporter they should get our authorization error
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                }
            }
        """

        result = self.schema.execute(query, variables={"id": self.reporter.id})
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access reporters."

        # An admin user should be able to get reporters
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": self.reporter.id},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data == {"reporter": {"firstName": "Jane"}}

    def test_get_queryset_called_on_foreignkey(self):
        # If a user tries to access a reporter through an article they should get our authorization error
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                    reporter {
                        firstName
                    }
                }
            }
        """

        result = self.schema.execute(query, variables={"id": self.articles[0].id})
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access reporters."

        # An admin user should be able to get reporters through an article
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                    reporter {
                        firstName
                    }
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": self.articles[0].id},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data["article"] == {
            "headline": "A fantastic article",
            "reporter": {"firstName": "Jane"},
        }

        # An admin user should not be able to access draft article through a reporter
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                    articles {
                        headline
                    }
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": self.reporter.id},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data["reporter"] == {
            "firstName": "Jane",
            "articles": [{"headline": "A fantastic article"}],
        }


class TestShouldCallGetQuerySetOnForeignKeyNode:
    """
    Check that the get_queryset method is called in both forward and reversed direction
    of a foreignkey on types using a node interface.
    (see issue #1111)
    """

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter
                fields = "__all__"
                interfaces = (Node,)

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("admin"):
                    return queryset
                raise Exception("Not authorized to access reporters.")

        class ArticleType(DjangoObjectType):
            class Meta:
                model = Article
                fields = "__all__"
                interfaces = (Node,)

            @classmethod
            def get_queryset(cls, queryset, info):
                return queryset.exclude(headline__startswith="Draft")

        class Query(graphene.ObjectType):
            reporter = Node.Field(ReporterType)
            article = Node.Field(ArticleType)

        self.schema = graphene.Schema(query=Query)

        self.reporter = Reporter.objects.create(first_name="Jane", last_name="Doe")

        self.articles = [
            Article.objects.create(
                headline="A fantastic article",
                reporter=self.reporter,
                editor=self.reporter,
            ),
            Article.objects.create(
                headline="Draft: My next best seller",
                reporter=self.reporter,
                editor=self.reporter,
            ),
        ]

    def test_get_queryset_called_on_node(self):
        # If a user tries to access an article it is fine as long as it's not a draft one
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                }
            }
        """
        # Non-draft
        result = self.schema.execute(
            query, variables={"id": to_global_id("ArticleType", self.articles[0].id)}
        )
        assert not result.errors
        assert result.data["article"] == {
            "headline": "A fantastic article",
        }
        # Draft
        result = self.schema.execute(
            query, variables={"id": to_global_id("ArticleType", self.articles[1].id)}
        )
        assert not result.errors
        assert result.data["article"] is None

        # If a non admin user tries to access a reporter they should get our authorization error
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                }
            }
        """

        result = self.schema.execute(
            query, variables={"id": to_global_id("ReporterType", self.reporter.id)}
        )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access reporters."

        # An admin user should be able to get reporters
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": to_global_id("ReporterType", self.reporter.id)},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data == {"reporter": {"firstName": "Jane"}}

    def test_get_queryset_called_on_foreignkey(self):
        # If a user tries to access a reporter through an article they should get our authorization error
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                    reporter {
                        firstName
                    }
                }
            }
        """

        result = self.schema.execute(
            query, variables={"id": to_global_id("ArticleType", self.articles[0].id)}
        )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access reporters."

        # An admin user should be able to get reporters through an article
        query = """
            query getArticle($id: ID!) {
                article(id: $id) {
                    headline
                    reporter {
                        firstName
                    }
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": to_global_id("ArticleType", self.articles[0].id)},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data["article"] == {
            "headline": "A fantastic article",
            "reporter": {"firstName": "Jane"},
        }

        # An admin user should not be able to access draft article through a reporter
        query = """
            query getReporter($id: ID!) {
                reporter(id: $id) {
                    firstName
                    articles {
                        edges {
                            node {
                                headline
                            }
                        }
                    }
                }
            }
        """

        result = self.schema.execute(
            query,
            variables={"id": to_global_id("ReporterType", self.reporter.id)},
            context_value={"admin": True},
        )
        assert not result.errors
        assert result.data["reporter"] == {
            "firstName": "Jane",
            "articles": {"edges": [{"node": {"headline": "A fantastic article"}}]},
        }


class TestShouldCallGetQuerySetOnOneToOne:
    @pytest.fixture(autouse=True)
    def setup_schema(self):
        class FilmDetailsType(DjangoObjectType):
            class Meta:
                model = FilmDetails
                fields = "__all__"

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("permission_get_film_details"):
                    return queryset
                raise Exception("Not authorized to access film details.")

        class FilmType(DjangoObjectType):
            class Meta:
                model = Film
                fields = "__all__"

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("permission_get_film"):
                    return queryset
                raise Exception("Not authorized to access film.")

        class Query(graphene.ObjectType):
            film_details = graphene.Field(
                FilmDetailsType, id=graphene.ID(required=True)
            )
            film = graphene.Field(FilmType, id=graphene.ID(required=True))

            def resolve_film_details(self, info, id):
                return (
                    FilmDetailsType.get_queryset(FilmDetails.objects, info)
                    .filter(id=id)
                    .last()
                )

            def resolve_film(self, info, id):
                return FilmType.get_queryset(Film.objects, info).filter(id=id).last()

        self.schema = graphene.Schema(query=Query)

        self.films = [
            Film.objects.create(
                genre="do",
            ),
            Film.objects.create(
                genre="ac",
            ),
        ]

        self.film_details = [
            FilmDetails.objects.create(
                film=self.films[0],
            ),
            FilmDetails.objects.create(
                film=self.films[1],
            ),
        ]

    def test_get_queryset_called_on_field(self):
        # A user tries to access a film
        query = """
            query getFilm($id: ID!) {
                film(id: $id) {
                    genre
                }
            }
        """

        # With `permission_get_film`
        result = self.schema.execute(
            query,
            variables={"id": self.films[0].id},
            context_value={"permission_get_film": True},
        )
        assert not result.errors
        assert result.data["film"] == {
            "genre": "DO",
        }

        # Without `permission_get_film`
        result = self.schema.execute(
            query,
            variables={"id": self.films[1].id},
            context_value={"permission_get_film": False},
        )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access film."

        # A user tries to access a film details
        query = """
            query getFilmDetails($id: ID!) {
                filmDetails(id: $id) {
                    location
                }
            }
        """

        # With `permission_get_film`
        result = self.schema.execute(
            query,
            variables={"id": self.film_details[0].id},
            context_value={"permission_get_film_details": True},
        )
        assert not result.errors
        assert result.data == {"filmDetails": {"location": ""}}

        # Without `permission_get_film`
        result = self.schema.execute(
            query,
            variables={"id": self.film_details[0].id},
            context_value={"permission_get_film_details": False},
        )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access film details."

    def test_get_queryset_called_on_foreignkey(self, django_assert_num_queries):
        # A user tries to access a film details through a film
        query = """
            query getFilm($id: ID!) {
                film(id: $id) {
                    genre
                    details {
                        location
                    }
                }
            }
        """

        # With `permission_get_film_details`
        with django_assert_num_queries(2):
            result = self.schema.execute(
                query,
                variables={"id": self.films[0].id},
                context_value={
                    "permission_get_film": True,
                    "permission_get_film_details": True,
                },
            )
        assert not result.errors
        assert result.data["film"] == {
            "genre": "DO",
            "details": {"location": ""},
        }

        # Without `permission_get_film_details`
        with django_assert_num_queries(1):
            result = self.schema.execute(
                query,
                variables={"id": self.films[0].id},
                context_value={
                    "permission_get_film": True,
                    "permission_get_film_details": False,
                },
            )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access film details."

        # A user tries to access a film through a film details
        query = """
            query getFilmDetails($id: ID!) {
                filmDetails(id: $id) {
                    location
                    film {
                        genre
                    }
                }
            }
        """

        # With `permission_get_film`
        with django_assert_num_queries(2):
            result = self.schema.execute(
                query,
                variables={"id": self.film_details[0].id},
                context_value={
                    "permission_get_film": True,
                    "permission_get_film_details": True,
                },
            )
        assert not result.errors
        assert result.data["filmDetails"] == {
            "location": "",
            "film": {"genre": "DO"},
        }

        # Without `permission_get_film`
        with django_assert_num_queries(1):
            result = self.schema.execute(
                query,
                variables={"id": self.film_details[1].id},
                context_value={
                    "permission_get_film": False,
                    "permission_get_film_details": True,
                },
            )
        assert len(result.errors) == 1
        assert result.errors[0].message == "Not authorized to access film."
