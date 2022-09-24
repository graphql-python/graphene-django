import pytest

import graphene
from graphene.relay import Node

from graphql_relay import to_global_id

from ..fields import DjangoConnectionField
from ..types import DjangoObjectType

from .models import Article, Reporter


class TestShouldCallGetQuerySetOnForeignKey:
    """
    Check that the get_queryset method is called in both forward and reversed direction
    of a foreignkey on types.
    (see issue #1111)
    """

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("admin"):
                    return queryset
                raise Exception("Not authorized to access reporters.")

        class ArticleType(DjangoObjectType):
            class Meta:
                model = Article

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
                interfaces = (Node,)

            @classmethod
            def get_queryset(cls, queryset, info):
                if info.context and info.context.get("admin"):
                    return queryset
                raise Exception("Not authorized to access reporters.")

        class ArticleType(DjangoObjectType):
            class Meta:
                model = Article
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
