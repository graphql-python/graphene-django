from collections import OrderedDict, defaultdict
from textwrap import dedent
from unittest.mock import patch

import pytest
from django.db import models

from graphene import Connection, Field, Interface, ObjectType, Schema, String
from graphene.relay import Node

from .. import registry
from ..filter import DjangoFilterConnectionField
from ..types import DjangoObjectType, DjangoObjectTypeOptions
from .models import (
    Article as ArticleModel,
    Reporter as ReporterModel,
)


class Reporter(DjangoObjectType):
    """Reporter description"""

    class Meta:
        model = ReporterModel
        fields = "__all__"


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
        fields = "__all__"


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
    assert fields[:-3] == [
        "id",
        "first_name",
        "last_name",
        "email",
        "pets",
        "a_choice",
        "fans",
        "reporter_type",
    ]
    assert sorted(fields[-3:]) == ["apnewsreporter", "articles", "films"]


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
            super().__init_subclass_with_meta__(**options)

    class Article(ArticleType):
        class Meta:
            model = ArticleModel
            fields = "__all__"

    assert isinstance(Article._meta, ArticleTypeOptions)


def test_schema_representation():
    expected = dedent(
        """\
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
          lang: TestsArticleLangChoices!
          importance: TestsArticleImportanceChoices
        }

        \"""An object with an ID\"""
        interface Node {
          \"""The ID of the object\"""
          id: ID!
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

        \"""An enumeration.\"""
        enum TestsArticleLangChoices {
          \"""Spanish\"""
          ES

          \"""English\"""
          EN
        }

        \"""An enumeration.\"""
        enum TestsArticleImportanceChoices {
          \"""Very important\"""
          A_1

          \"""Not as important\"""
          A_2
        }

        \"""Reporter description\"""
        type Reporter {
          id: ID!
          firstName: String!
          lastName: String!
          email: String!
          pets: [Reporter!]!
          aChoice: TestsReporterAChoiceChoices
          reporterType: TestsReporterReporterTypeChoices
          articles(offset: Int, before: String, after: String, first: Int, last: Int): ArticleConnection!
        }

        \"""An enumeration.\"""
        enum TestsReporterAChoiceChoices {
          \"""this\"""
          A_1

          \"""that\"""
          A_2
        }

        \"""An enumeration.\"""
        enum TestsReporterReporterTypeChoices {
          \"""Regular\"""
          A_1

          \"""CNN Reporter\"""
          A_2
        }

        type ArticleConnection {
          \"""Pagination data for this connection.\"""
          pageInfo: PageInfo!

          \"""Contains the nodes in this connection.\"""
          edges: [ArticleEdge]!
          test: String
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

        \"""A Relay edge containing a `Article` and its cursor.\"""
        type ArticleEdge {
          \"""The item at the end of the edge\"""
          node: Article

          \"""A cursor for use in pagination\"""
          cursor: String!
        }

        type RootQuery {
          node(
            \"""The ID of the object\"""
            id: ID!
          ): Node
        }"""
    )
    assert str(schema) == expected


def with_local_registry(func):
    def inner(*args, **kwargs):
        old = registry.get_global_registry()
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
    with pytest.warns(DeprecationWarning):

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
def test_django_objecttype_fields_empty():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            fields = ()

    fields = list(Reporter._meta.fields.keys())
    assert fields == []


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
    with pytest.warns(DeprecationWarning):

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
                exclude = "foo"


@with_local_registry
def test_django_objecttype_fields_exist_on_model():
    with pytest.warns(UserWarning, match=r"Field name .* doesn't exist"):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ["first_name", "foo", "email"]

    with pytest.warns(
        UserWarning,
        match=r"Field name .* matches an attribute on Django model .* but it's not a model field",
    ) as record:

        class Reporter2(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ["first_name", "some_method", "email"]

    # Don't warn if selecting a custom field
    with pytest.warns(None) as record:

        class Reporter3(DjangoObjectType):
            custom_field = String()

            class Meta:
                model = ReporterModel
                fields = ["first_name", "custom_field", "email"]

    assert len(record) == 0


@with_local_registry
def test_django_objecttype_exclude_fields_exist_on_model():
    with pytest.warns(
        UserWarning,
        match=r"Django model .* does not have a field or attribute named .*",
    ):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["foo"]

    # Don't warn if selecting a custom field
    with pytest.warns(
        UserWarning,
        match=r"Excluding the custom field .* on DjangoObjectType .* has no effect.",
    ):

        class Reporter3(DjangoObjectType):
            custom_field = String()

            class Meta:
                model = ReporterModel
                exclude = ["custom_field"]

    # Don't warn on exclude fields
    with pytest.warns(None) as record:

        class Reporter4(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email", "first_name"]

    assert len(record) == 0


@with_local_registry
def test_django_objecttype_neither_fields_nor_exclude():
    with pytest.warns(
        DeprecationWarning,
        match=r"Creating a DjangoObjectType without either the `fields` "
        "or the `exclude` option is deprecated.",
    ):

        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel

    with pytest.warns(None) as record:

        class Reporter2(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ["email"]

    assert len(record) == 0

    with pytest.warns(None) as record:

        class Reporter3(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email"]

    assert len(record) == 0


def custom_enum_name(field):
    return f"CustomEnum{field.name.title()}"


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
                fields = "__all__"

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: String!
              cuteness: Int!
            }"""
        )

    def test_django_objecttype_convert_choices_enum_list(self, PetModel):
        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = ["kind"]
                fields = "__all__"

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: TestsPetModelKindChoices!
              cuteness: Int!
            }

            \"""An enumeration.\"""
            enum TestsPetModelKindChoices {
              \"""Cat\"""
              CAT

              \"""Dog\"""
              DOG
            }"""
        )

    def test_django_objecttype_convert_choices_enum_empty_list(self, PetModel):
        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = []
                fields = "__all__"

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: String!
              cuteness: Int!
            }"""
        )

    def test_django_objecttype_convert_choices_enum_naming_collisions(
        self, PetModel, graphene_settings
    ):
        class PetModelKind(DjangoObjectType):
            class Meta:
                model = PetModel
                fields = ["id", "kind"]

        class Query(ObjectType):
            pet = Field(PetModelKind)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: PetModelKind
            }

            type PetModelKind {
              id: ID!
              kind: TestsPetModelKindChoices!
            }

            \"""An enumeration.\"""
            enum TestsPetModelKindChoices {
              \"""Cat\"""
              CAT

              \"""Dog\"""
              DOG
            }"""
        )

    def test_django_objecttype_choices_custom_enum_name(
        self, PetModel, graphene_settings
    ):
        graphene_settings.DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME = (
            "graphene_django.tests.test_types.custom_enum_name"
        )

        class PetModelKind(DjangoObjectType):
            class Meta:
                model = PetModel
                fields = ["id", "kind"]

        class Query(ObjectType):
            pet = Field(PetModelKind)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: PetModelKind
            }

            type PetModelKind {
              id: ID!
              kind: CustomEnumKind!
            }

            \"""An enumeration.\"""
            enum CustomEnumKind {
              \"""Cat\"""
              CAT

              \"""Dog\"""
              DOG
            }"""
        )

    def test_django_objecttype_convert_choices_global_false(
        self, graphene_settings, PetModel
    ):
        graphene_settings.DJANGO_CHOICE_FIELD_ENUM_CONVERT = False

        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                fields = "__all__"

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: String!
              cuteness: Int!
            }"""
        )

    def test_django_objecttype_convert_choices_true_global_false(
        self, graphene_settings, PetModel
    ):
        graphene_settings.DJANGO_CHOICE_FIELD_ENUM_CONVERT = False

        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                fields = "__all__"
                convert_choices_to_enum = True

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: TestsPetModelKindChoices!
              cuteness: TestsPetModelCutenessChoices!
            }

            \"""An enumeration.\"""
            enum TestsPetModelKindChoices {
              \"""Cat\"""
              CAT

              \"""Dog\"""
              DOG
            }

            \"""An enumeration.\"""
            enum TestsPetModelCutenessChoices {
              \"""Kind of cute\"""
              A_1

              \"""Pretty cute\"""
              A_2

              \"""OMG SO CUTE!!!\"""
              A_3
            }"""
        )

    def test_django_objecttype_convert_choices_enum_list_global_false(
        self, graphene_settings, PetModel
    ):
        graphene_settings.DJANGO_CHOICE_FIELD_ENUM_CONVERT = False

        class Pet(DjangoObjectType):
            class Meta:
                model = PetModel
                convert_choices_to_enum = ["kind"]
                fields = "__all__"

        class Query(ObjectType):
            pet = Field(Pet)

        schema = Schema(query=Query)

        assert str(schema) == dedent(
            """\
            type Query {
              pet: Pet
            }

            type Pet {
              id: ID!
              kind: TestsPetModelKindChoices!
              cuteness: Int!
            }

            \"""An enumeration.\"""
            enum TestsPetModelKindChoices {
              \"""Cat\"""
              CAT

              \"""Dog\"""
              DOG
            }"""
        )


@with_local_registry
def test_django_objecttype_name_connection_propagation():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            name = "CustomReporterName"
            fields = "__all__"
            filter_fields = ["email"]
            interfaces = (Node,)

    class Query(ObjectType):
        reporter = Node.Field(Reporter)
        reporters = DjangoFilterConnectionField(Reporter)

    assert Reporter._meta.name == "CustomReporterName"
    schema = str(Schema(query=Query))

    assert "type CustomReporterName implements Node {" in schema
    assert "type CustomReporterNameConnection {" in schema
    assert "type CustomReporterNameEdge {" in schema

    assert "type Reporter implements Node {" not in schema
    assert "type ReporterConnection {" not in schema
    assert "type ReporterEdge {" not in schema
