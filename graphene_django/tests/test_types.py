from collections import OrderedDict, defaultdict
from textwrap import dedent

import pytest
from django.db import models
from mock import patch

from graphene import Connection, Field, Interface, ObjectType, Schema, String
from graphene.relay import Node

from .. import registry
from ..types import DjangoObjectType, DjangoObjectTypeOptions
from .models import Article as ArticleModel
from .models import Reporter as ReporterModel

registry.reset_global_registry()


class Reporter(DjangoObjectType):
    """Reporter description"""

    class Meta:
        model = ReporterModel


class ArticleConnection(Connection):
    """Article Connection"""

    test = String()

    def resolve_test():
        return "test"

    class Meta:
        abstract = True


class Article(DjangoObjectType):
    """Article description"""

    class Meta:
        model = ArticleModel
        interfaces = (Node,)
        connection_class = ArticleConnection


class RootQuery(ObjectType):
    node = Node.Field()


schema = Schema(query=RootQuery, types=[Article, Reporter])


def test_django_interface():
    assert issubclass(Node, Interface)
    assert issubclass(Node, Node)


@patch("graphene_django.tests.models.Article.objects.get", return_value=Article(id=1))
def test_django_get_node(get):
    article = Article.get_node(None, 1)
    get.assert_called_with(pk=1)
    assert article.id == 1


def test_django_objecttype_map_correct_fields():
    fields = Reporter._meta.fields
    fields = list(fields.keys())
    assert fields[:-2] == [
        "id",
        "first_name",
        "last_name",
        "email",
        "pets",
        "a_choice",
        "reporter_type",
    ]
    assert sorted(fields[-2:]) == ["articles", "films"]


def test_django_objecttype_with_node_have_correct_fields():
    fields = Article._meta.fields
    assert list(fields.keys()) == [
        "id",
        "headline",
        "pub_date",
        "pub_date_time",
        "reporter",
        "editor",
        "lang",
        "importance",
    ]


def test_django_objecttype_with_custom_meta():
    class ArticleTypeOptions(DjangoObjectTypeOptions):
        """Article Type Options"""

    class ArticleType(DjangoObjectType):
        class Meta:
            abstract = True

        @classmethod
        def __init_subclass_with_meta__(cls, **options):
            options.setdefault("_meta", ArticleTypeOptions(cls))
            super(ArticleType, cls).__init_subclass_with_meta__(**options)

    class Article(ArticleType):
        class Meta:
            model = ArticleModel

    assert isinstance(Article._meta, ArticleTypeOptions)


def test_schema_representation():
    expected = """
schema {
  query: RootQuery
}

\"""Article description\"""
type Article implements Node {
  \"""The ID of the object\"""
  id: ID!
  headline: String!
  pubDate: Date!
  pubDateTime: DateTime!
  reporter: Reporter!
  editor: Reporter!

  \"""Language\"""
  lang: ArticleLang!
  importance: ArticleImportance
}

type ArticleConnection {
  \"""Pagination data for this connection.\"""
  pageInfo: PageInfo!

  \"""Contains the nodes in this connection.\"""
  edges: [ArticleEdge]!
  test: String
}

\"""A Relay edge containing a `Article` and its cursor.\"""
type ArticleEdge {
  \"""The item at the end of the edge\"""
  node: Article

  \"""A cursor for use in pagination\"""
  cursor: String!
}

\"""An enumeration.\"""
enum ArticleImportance {
  \"""Very important\"""
  A_1

  \"""Not as important\"""
  A_2
}

\"""An enumeration.\"""
enum ArticleLang {
  \"""Spanish\"""
  ES

  \"""English\"""
  EN
}

\"""
The `Date` scalar type represents a Date
value as specified by
[iso8601](https://en.wikipedia.org/wiki/ISO_8601).
\"""
scalar Date

\"""
The `DateTime` scalar type represents a DateTime
value as specified by
[iso8601](https://en.wikipedia.org/wiki/ISO_8601).
\"""
scalar DateTime

\"""An object with an ID\"""
interface Node {
  \"""The ID of the object\"""
  id: ID!
}

\"""
The Relay compliant `PageInfo` type, containing data necessary to paginate this connection.
\"""
type PageInfo {
  \"""When paginating forwards, are there more items?\"""
  hasNextPage: Boolean!

  \"""When paginating backwards, are there more items?\"""
  hasPreviousPage: Boolean!

  \"""When paginating backwards, the cursor to continue.\"""
  startCursor: String

  \"""When paginating forwards, the cursor to continue.\"""
  endCursor: String
}

\"""Reporter description\"""
type Reporter {
  id: ID!
  firstName: String!
  lastName: String!
  email: String!
  pets: [Reporter!]!
  aChoice: ReporterAChoice
  reporterType: ReporterReporterType
  articles(before: String = null, after: String = null, first: Int = null, last: Int = null): ArticleConnection!
}

\"""An enumeration.\"""
enum ReporterAChoice {
  \"""this\"""
  A_1

  \"""that\"""
  A_2
}

\"""An enumeration.\"""
enum ReporterReporterType {
  \"""Regular\"""
  A_1

  \"""CNN Reporter\"""
  A_2
}

type RootQuery {
  node(
    \"""The ID of the object\"""
    id: ID!
  ): Node
}
""".lstrip()
    assert str(schema) == expected


def with_local_registry(func):
    def inner(*args, **kwargs):
        old = registry.get_global_registry()
        registry.reset_global_registry()
        try:
            retval = func(*args, **kwargs)
        except Exception as e:
            registry.registry = old
            raise e
        else:
            registry.registry = old
            return retval

    return inner


@with_local_registry
def test_django_objecttype_only_fields():
    with pytest.warns(PendingDeprecationWarning):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                only_fields = ("id", "email", "films")

    fields = list(Reporter._meta.fields.keys())
    assert fields == ["id", "email", "films"]


@with_local_registry
def test_django_objecttype_fields():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            fields = ("id", "email", "films")

    fields = list(Reporter._meta.fields.keys())
    assert fields == ["id", "email", "films"]


@with_local_registry
def test_django_objecttype_only_fields_and_fields():
    with pytest.raises(Exception):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                only_fields = ("id", "email", "films")
                fields = ("id", "email", "films")


@with_local_registry
def test_django_objecttype_all_fields():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            fields = "__all__"

    fields = list(Reporter._meta.fields.keys())
    assert len(fields) == len(ReporterModel._meta.get_fields())


@with_local_registry
def test_django_objecttype_exclude_fields():
    with pytest.warns(PendingDeprecationWarning):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude_fields = ["email"]

    fields = list(Reporter._meta.fields.keys())
    assert "email" not in fields


@with_local_registry
def test_django_objecttype_exclude():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            exclude = ["email"]

    fields = list(Reporter._meta.fields.keys())
    assert "email" not in fields


@with_local_registry
def test_django_objecttype_exclude_fields_and_exclude():
    with pytest.raises(Exception):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email"]
                exclude_fields = ["email"]


@with_local_registry
def test_django_objecttype_exclude_and_only():
    with pytest.raises(AssertionError):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email"]
                fields = ["id"]


@with_local_registry
def test_django_objecttype_fields_exclude_type_checking():
    with pytest.raises(TypeError):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = "foo"

    with pytest.raises(TypeError):

        class Reporter2(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = "foo"


class TestDjangoObjectType:
    @pytest.fixture
    def PetModel(self):
        class PetModel(models.Model):
            kind = models.CharField(choices=(("cat", "Cat"), ("dog", "Dog")))
            cuteness = models.IntegerField(
                choices=((1, "Kind of cute"), (2, "Pretty cute"), (3, "OMG SO CUTE!!!"))
            )

        yield PetModel

        # Clear Django model cache so we don't get warnings when creating the
        # model multiple times
        PetModel._meta.apps.all_models = defaultdict(OrderedDict)

    def test_django_objecttype_convert_choices_enum_false(self, PetModel):
        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = False

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
        type Pet {
          id: ID!
          kind: String!
          cuteness: Int!
        }

        type Query {
          pet: Pet
        }
        """
        )

    def test_django_objecttype_convert_choices_enum_list(self, PetModel):
        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = ["kind"]

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
        type Pet {
          id: ID!
          kind: PetModelKind!
          cuteness: Int!
        }

        \"""An enumeration.\"""
        enum PetModelKind {
          \"""Cat\"""
          CAT

          \"""Dog\"""
          DOG
        }

        type Query {
          pet: Pet
        }
        """
        )

    def test_django_objecttype_convert_choices_enum_empty_list(self, PetModel):
        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = []

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
        type Pet {
          id: ID!
          kind: String!
          cuteness: Int!
        }

        type Query {
          pet: Pet
        }
        """
        )
