import pytest

import graphene
from graphene.relay import Node

from graphene_django import DjangoObjectType, DjangoConnectionField
from graphene_django.tests.models import Article, Reporter
from graphene_django.utils import DJANGO_FILTER_INSTALLED

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    from graphene_django.filter import DjangoFilterConnectionField
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )


@pytest.fixture
def schema():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = {
                "lang": ["exact", "in"],
                "reporter__a_choice": ["exact", "in"],
            }

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)
        all_articles = DjangoFilterConnectionField(ArticleType)

    schema = graphene.Schema(query=Query)
    return schema


@pytest.fixture
def reporter_article_data():
    john = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )
    jane = Reporter.objects.create(
        first_name="Jane", last_name="Doe", email="janedoe@example.com", a_choice=2
    )
    Article.objects.create(
        headline="Article Node 1", reporter=john, editor=john, lang="es"
    )
    Article.objects.create(
        headline="Article Node 2", reporter=john, editor=john, lang="en"
    )
    Article.objects.create(
        headline="Article Node 3", reporter=jane, editor=jane, lang="en"
    )


def test_filter_enum_on_connection(schema, reporter_article_data):
    """
    Check that we can filter with enums on a connection.
    """
    query = """
        query {
            allArticles(lang: ES) {
                edges {
                    node {
                        headline
                    }
                }
            }
        }
    """

    expected = {
        "allArticles": {
            "edges": [
                {"node": {"headline": "Article Node 1"}},
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_filter_on_foreign_key_enum_field(schema, reporter_article_data):
    """
    Check that we can filter with enums on a field from a foreign key.
    """
    query = """
        query {
            allArticles(reporter_AChoice: A_1) {
                edges {
                    node {
                        headline
                    }
                }
            }
        }
    """

    expected = {
        "allArticles": {
            "edges": [
                {"node": {"headline": "Article Node 1"}},
                {"node": {"headline": "Article Node 2"}},
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_filter_enum_field_schema_type(schema):
    """
    Check that the type in the filter is an enum like on the object type.
    """
    schema_str = str(schema)

    assert (
        '''type ArticleType implements Node {
  """The ID of the object"""
  id: ID!
  headline: String!
  pubDate: Date!
  pubDateTime: DateTime!
  reporter: ReporterType!
  editor: ReporterType!

  """Language"""
  lang: TestsArticleLangChoices!
  importance: TestsArticleImportanceChoices
}'''
        in schema_str
    )

    filters = {
        "offset": "Int",
        "before": "String",
        "after": "String",
        "first": "Int",
        "last": "Int",
        "lang": "TestsArticleLangChoices",
        "lang_In": "[TestsArticleLangChoices]",
        "reporter_AChoice": "TestsReporterAChoiceChoices",
        "reporter_AChoice_In": "[TestsReporterAChoiceChoices]",
    }
    filters_str = ", ".join(
        [f"{filter_field}: {gql_type}" for filter_field, gql_type in filters.items()]
    )
    assert f"  allArticles({filters_str}): ArticleTypeConnection\n" in schema_str
