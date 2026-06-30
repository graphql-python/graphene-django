import warnings
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

    def resolve_test(parent):
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
        "typed_choice",
        "class_choice",
        "callable_choice",
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
          typedChoice: TestsReporterTypedChoiceChoices
          classChoice: TestsReporterClassChoiceChoices
          callableChoice: TestsReporterCallableChoiceChoices
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
        enum TestsReporterTypedChoiceChoices {
          \"""Choice This\"""
          A_1

          \"""Choice That\"""
          A_2
        }

        \"""An enumeration.\"""
        enum TestsReporterClassChoiceChoices {
          \"""Choice This\"""
          A_1

          \"""Choice That\"""
          A_2
        }

        \"""An enumeration.\"""
        enum TestsReporterCallableChoiceChoices {
          \"""Choice This\"""
          THIS

          \"""Choice That\"""
          THAT
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
    ):

        class Reporter2(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ["first_name", "some_method", "email"]

    # Don't warn if selecting a custom field
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class Reporter3(DjangoObjectType):
            custom_field = String()

            class Meta:
                model = ReporterModel
                fields = ["first_name", "custom_field", "email"]


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
    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class Reporter4(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email", "first_name"]


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

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class Reporter2(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ["email"]

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class Reporter3(DjangoObjectType):
            class Meta:
                model = ReporterModel
                exclude = ["email"]


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


class TestValidateFieldsHelpers:
    """Direct unit tests for the ``validate_fields`` extraction in
    :mod:`graphene_django.types`.

    These tests exercise :func:`_validate_only_fields`,
    :func:`_validate_exclude_fields`, and the
    :func:`validate_fields` orchestrator in isolation — without going
    through ``DjangoObjectType.__init_subclass_with_meta__`` — so each
    warning case fails a focused test rather than only being detected
    via integration coverage on type construction.

    Scenarios covered:

    * ``_validate_only_fields``
        - happy path: requested name is in ``all_field_names`` (no warning)
        - requested name resolves to a non-field model attribute (warning
          about "matches an attribute")
        - requested name is unknown to the model (warning about "doesn't
          exist on Django model")
        - ``only_fields=None`` is a no-op
        - ``only_fields=ALL_FIELDS`` is normalised to a no-op by the
          orchestrator and is therefore exercised through ``validate_fields``
    * ``_validate_exclude_fields``
        - happy path: excluded name corresponds to a real model field
          (no warning)
        - excluded name is a custom field on the type (warning about
          "Excluding the custom field")
        - excluded name is unknown to the model (warning about "does not
          have a field or attribute")
        - ``exclude_fields=None`` is a no-op
    * ``validate_fields`` orchestrator
        - ``ALL_FIELDS`` sentinel for ``only_fields`` is normalised to
          empty iteration (and therefore emits no warning)
        - delegates to both helpers (combined-warning happy path)

    The tests assert on the message text via ``pytest.warns(..., match=...)``
    so a regression in the error wording also fails a focused test.
    """

    @staticmethod
    def _all_field_names():
        """Reusable set of "real" converted-field names for ReporterModel."""
        return {"first_name", "last_name", "email", "pets", "custom_field"}

    def test_only_fields_known_field_emits_no_warning(self):
        """
        Name: only_fields, known field, no warning
        Description: A name present in ``all_field_names`` short-circuits via
            ``continue`` and emits no warning.
        Assumptions: ``first_name`` is one of the converted fields supplied
            in ``all_field_names``.
        Expectations: ``warnings.simplefilter("error")`` does not raise — i.e.
            no warning is emitted.
        """
        from ..types import _validate_only_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _validate_only_fields(
                ["first_name"], self._all_field_names(), ReporterModel, "TestType"
            )

    def test_only_fields_model_attribute_warns_about_attribute(self):
        """
        Name: only_fields, attribute-not-field, attribute warning
        Description: A name that exists as a Python attribute on the model but
            is not a model field (e.g. ``Reporter.some_method``) must produce
            the "matches an attribute" warning so the user knows to declare
            the field on the type.
        Assumptions: ``Reporter.some_method`` is defined on the model and is
            not in ``all_field_names``.
        Expectations: A ``UserWarning`` whose message matches the
            "matches an attribute on Django model" wording is emitted.
        """
        from ..types import _validate_only_fields

        with pytest.warns(
            UserWarning,
            match=r"matches an attribute on Django model .* but it's not a model field",
        ):
            _validate_only_fields(
                ["some_method"], self._all_field_names(), ReporterModel, "TestType"
            )

    def test_only_fields_unknown_name_warns_about_missing_field(self):
        """
        Name: only_fields, unknown name, missing-field warning
        Description: A name that is neither a converted field nor any
            attribute on the model must produce the "doesn't exist on
            Django model" warning so the user knows it is a typo or stale
            entry in ``Meta.fields``.
        Assumptions: ``"foo"`` is not a field of ReporterModel and is not
            in ``all_field_names``.
        Expectations: A ``UserWarning`` whose message matches the
            "doesn't exist on Django model" wording is emitted.
        """
        from ..types import _validate_only_fields

        with pytest.warns(
            UserWarning,
            match=r"Field name \"foo\" doesn't exist on Django model",
        ):
            _validate_only_fields(
                ["foo"], self._all_field_names(), ReporterModel, "TestType"
            )

    def test_only_fields_none_is_a_noop(self):
        """
        Name: only_fields, None argument, no-op
        Description: Passing ``None`` for ``only_fields`` must iterate over
            an empty sequence and emit no warning.
        Assumptions: The helper uses ``only_fields or ()`` so ``None`` is
            normalised at call site.
        Expectations: ``warnings.simplefilter("error")`` does not raise.
        """
        from ..types import _validate_only_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _validate_only_fields(
                None, self._all_field_names(), ReporterModel, "TestType"
            )

    def test_exclude_fields_real_model_field_emits_no_warning(self):
        """
        Name: exclude_fields, real model field, no warning
        Description: Excluding a name that exists on the model and is not
            also a custom field on the type is the happy path and produces
            no warning.
        Assumptions: ``"first_name"`` is on ReporterModel and is not in the
            ``all_field_names`` set passed in (we deliberately use a set
            without it to model "this is a real field, not a custom one").
        Expectations: ``warnings.simplefilter("error")`` does not raise.
        """
        from ..types import _validate_exclude_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _validate_exclude_fields(
                ["first_name"],
                {"custom_field"},
                ReporterModel,
                "TestType",
            )

    def test_exclude_fields_custom_field_warns_about_no_effect(self):
        """
        Name: exclude_fields, custom field, "no effect" warning
        Description: Excluding a name that maps to a custom field declared
            directly on the ``DjangoObjectType`` has no effect (since
            ``Meta.exclude`` only filters auto-converted model fields), so
            a warning must be emitted.
        Assumptions: ``"custom_field"`` is in the supplied ``all_field_names``
            (i.e. it was added by the user as a custom field on the type).
        Expectations: A ``UserWarning`` whose message matches the
            "Excluding the custom field" wording is emitted.
        """
        from ..types import _validate_exclude_fields

        with pytest.warns(
            UserWarning,
            match=r"Excluding the custom field \"custom_field\" on DjangoObjectType",
        ):
            _validate_exclude_fields(
                ["custom_field"],
                self._all_field_names(),
                ReporterModel,
                "TestType",
            )

    def test_exclude_fields_unknown_name_warns_about_missing_attribute(self):
        """
        Name: exclude_fields, unknown name, missing-attribute warning
        Description: Excluding a name that is neither a custom field nor any
            attribute of the model must produce the "does not have a field
            or attribute" warning to flag the typo or stale entry.
        Assumptions: ``"foo"`` does not exist on ReporterModel and is not in
            ``all_field_names``.
        Expectations: A ``UserWarning`` matching the "does not have a field
            or attribute" wording is emitted.
        """
        from ..types import _validate_exclude_fields

        with pytest.warns(
            UserWarning,
            match=r"does not have a field or attribute named \"foo\"",
        ):
            _validate_exclude_fields(
                ["foo"], self._all_field_names(), ReporterModel, "TestType"
            )

    def test_exclude_fields_none_is_a_noop(self):
        """
        Name: exclude_fields, None argument, no-op
        Description: Passing ``None`` for ``exclude_fields`` must iterate
            over an empty sequence and emit no warning.
        Assumptions: The helper uses ``exclude_fields or ()`` so ``None`` is
            normalised at call site.
        Expectations: ``warnings.simplefilter("error")`` does not raise.
        """
        from ..types import _validate_exclude_fields

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _validate_exclude_fields(
                None, self._all_field_names(), ReporterModel, "TestType"
            )

    def test_validate_fields_normalises_all_fields_sentinel(self):
        """
        Name: validate_fields, ALL_FIELDS sentinel
        Description: The orchestrator must treat ``only_fields=ALL_FIELDS``
            as an empty iteration so that the request "all fields" never
            triggers a per-name warning loop.
        Assumptions: :data:`graphene_django.types.ALL_FIELDS` is the sentinel
            used to mean "all fields".
        Expectations: No warning is emitted even though the
            ``ALL_FIELDS`` string itself is not in ``all_field_names``.
        """
        from ..types import ALL_FIELDS, validate_fields

        fake_fields = {"first_name": object(), "last_name": object()}
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            validate_fields(
                "TestType",
                ReporterModel,
                fake_fields,
                only_fields=ALL_FIELDS,
                exclude_fields=None,
            )

    def test_validate_fields_delegates_to_both_helpers(self):
        """
        Name: validate_fields, delegates to both helpers
        Description: The orchestrator must forward both ``only_fields`` and
            ``exclude_fields`` to their respective helpers, so an invalid
            entry in either list still surfaces a warning.
        Assumptions: ``"foo"`` is unknown to the model in both contexts.
        Expectations: Two warnings are emitted in a single call: one for
            the missing-from-fields name and one for the
            missing-from-exclude name.
        """
        from ..types import validate_fields

        fake_fields = {"first_name": object()}
        with warnings.catch_warnings(record=True) as recorded:
            warnings.simplefilter("always")
            validate_fields(
                "TestType",
                ReporterModel,
                fake_fields,
                only_fields=["foo"],
                exclude_fields=["bar"],
            )

        messages = [str(w.message) for w in recorded]
        assert any("Field name \"foo\" doesn't exist" in m for m in messages), messages
        assert any(
            "does not have a field or attribute named \"bar\"" in m for m in messages
        ), messages
