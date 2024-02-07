from collections import namedtuple

import pytest
from django.db import models
from django.utils.translation import gettext_lazy as _
from pytest import raises

import graphene
from graphene import NonNull
from graphene.relay import ConnectionField, Node
from graphene.types.datetime import Date, DateTime, Time
from graphene.types.json import JSONString
from graphene.types.scalars import BigInt

from ..compat import (
    ArrayField,
    HStoreField,
    MissingType,
    RangeField,
)
from ..converter import (
    convert_django_field,
    convert_django_field_with_choices,
    generate_enum_name,
)
from ..registry import Registry
from ..types import DjangoObjectType
from .models import Article, Film, FilmDetails, Reporter

# from graphene.core.types.custom_scalars import DateTime, Time, JSONString


def assert_conversion(django_field, graphene_field, *args, **kwargs):
    _kwargs = {**kwargs, "help_text": "Custom Help Text"}
    if "null" not in kwargs:
        _kwargs["null"] = True
    field = django_field(*args, **_kwargs)
    graphene_type = convert_django_field(field)
    assert isinstance(graphene_type, graphene_field)
    field = graphene_type.Field()
    assert field.description == "Custom Help Text"

    _kwargs = kwargs.copy()
    if "null" not in kwargs:
        _kwargs["null"] = False
    nonnull_field = django_field(*args, **_kwargs)
    if not nonnull_field.null:
        nonnull_graphene_type = convert_django_field(nonnull_field)
        nonnull_field = nonnull_graphene_type.Field()
        assert isinstance(nonnull_field.type, graphene.NonNull)
        return nonnull_field
    return field


def test_should_unknown_django_field_raise_exception():
    with raises(Exception) as excinfo:
        convert_django_field(None)
    assert "Don't know how to convert the Django field" in str(excinfo.value)


def test_should_date_time_convert_string():
    assert_conversion(models.DateTimeField, DateTime)


def test_should_date_convert_string():
    assert_conversion(models.DateField, Date)


def test_should_time_convert_string():
    assert_conversion(models.TimeField, Time)


def test_should_char_convert_string():
    assert_conversion(models.CharField, graphene.String)


def test_should_text_convert_string():
    assert_conversion(models.TextField, graphene.String)


def test_should_email_convert_string():
    assert_conversion(models.EmailField, graphene.String)


def test_should_slug_convert_string():
    assert_conversion(models.SlugField, graphene.String)


def test_should_url_convert_string():
    assert_conversion(models.URLField, graphene.String)


def test_should_ipaddress_convert_string():
    assert_conversion(models.GenericIPAddressField, graphene.String)


def test_should_file_convert_string():
    assert_conversion(models.FileField, graphene.String)


def test_should_image_convert_string():
    assert_conversion(models.ImageField, graphene.String)


def test_should_file_path_field_convert_string():
    assert_conversion(models.FilePathField, graphene.String)


def test_should_auto_convert_id():
    assert_conversion(models.AutoField, graphene.ID, primary_key=True)


def test_should_big_auto_convert_id():
    assert_conversion(models.BigAutoField, graphene.ID, primary_key=True)


def test_should_small_auto_convert_id():
    if hasattr(models, "SmallAutoField"):
        assert_conversion(models.SmallAutoField, graphene.ID, primary_key=True)


def test_should_uuid_convert_id():
    assert_conversion(models.UUIDField, graphene.UUID)


def test_should_auto_convert_duration():
    assert_conversion(models.DurationField, graphene.Float)


def test_should_positive_integer_convert_int():
    assert_conversion(models.PositiveIntegerField, graphene.Int)


def test_should_positive_small_convert_int():
    assert_conversion(models.PositiveSmallIntegerField, graphene.Int)


def test_should_small_integer_convert_int():
    assert_conversion(models.SmallIntegerField, graphene.Int)


def test_should_big_integer_convert_big_int():
    assert_conversion(models.BigIntegerField, BigInt)


def test_should_integer_convert_int():
    assert_conversion(models.IntegerField, graphene.Int)


def test_should_boolean_convert_boolean():
    assert_conversion(models.BooleanField, graphene.Boolean, null=True)


def test_should_boolean_convert_non_null_boolean():
    field = assert_conversion(models.BooleanField, graphene.Boolean, null=False)
    assert isinstance(field.type, graphene.NonNull)
    assert field.type.of_type == graphene.Boolean


def test_should_nullboolean_convert_boolean():
    assert_conversion(models.NullBooleanField, graphene.Boolean)


def test_field_with_choices_convert_enum():
    field = models.CharField(
        help_text="Language", choices=(("es", "Spanish"), ("en", "English"))
    )

    class TranslatedModel(models.Model):
        language = field

        class Meta:
            app_label = "test"

    graphene_type = convert_django_field_with_choices(field).type.of_type
    assert graphene_type._meta.name == "TestTranslatedModelLanguageChoices"
    assert graphene_type._meta.enum.__members__["ES"].value == "es"
    assert graphene_type._meta.enum.__members__["ES"].description == "Spanish"
    assert graphene_type._meta.enum.__members__["EN"].value == "en"
    assert graphene_type._meta.enum.__members__["EN"].description == "English"


def test_field_with_callable_choices_convert_enum():
    def get_choices():
        return ("es", "Spanish"), ("en", "English")

    field = models.CharField(help_text="Language", choices=get_choices)

    class TranslatedModel(models.Model):
        language = field

        class Meta:
            app_label = "test"

    graphene_type = convert_django_field_with_choices(field).type.of_type
    assert graphene_type._meta.name == "TestTranslatedModelLanguageChoices"
    assert graphene_type._meta.enum.__members__["ES"].value == "es"
    assert graphene_type._meta.enum.__members__["ES"].description == "Spanish"
    assert graphene_type._meta.enum.__members__["EN"].value == "en"
    assert graphene_type._meta.enum.__members__["EN"].description == "English"


def test_field_with_grouped_choices():
    field = models.CharField(
        help_text="Language",
        choices=(("Europe", (("es", "Spanish"), ("en", "English"))),),
    )

    class GroupedChoicesModel(models.Model):
        language = field

        class Meta:
            app_label = "test"

    convert_django_field_with_choices(field)


def test_field_with_choices_gettext():
    field = models.CharField(
        help_text="Language", choices=(("es", _("Spanish")), ("en", _("English")))
    )

    class TranslatedChoicesModel(models.Model):
        language = field

        class Meta:
            app_label = "test"

    convert_django_field_with_choices(field)


def test_field_with_choices_collision():
    field = models.CharField(
        help_text="Timezone",
        choices=(
            ("Etc/GMT+1+2", "Fake choice to produce double collision"),
            ("Etc/GMT+1", "Greenwich Mean Time +1"),
            ("Etc/GMT-1", "Greenwich Mean Time -1"),
        ),
    )

    class CollisionChoicesModel(models.Model):
        timezone = field

        class Meta:
            app_label = "test"

    convert_django_field_with_choices(field)


def test_field_with_choices_convert_enum_false():
    field = models.CharField(
        help_text="Language", choices=(("es", "Spanish"), ("en", "English"))
    )

    class TranslatedModel(models.Model):
        language = field

        class Meta:
            app_label = "test"

    graphene_type = convert_django_field_with_choices(
        field, convert_choices_to_enum=False
    )
    assert isinstance(graphene_type, graphene.String)


def test_should_float_convert_float():
    assert_conversion(models.FloatField, graphene.Float)


def test_should_float_convert_decimal():
    assert_conversion(models.DecimalField, graphene.Decimal)


def test_should_manytomany_convert_connectionorlist():
    registry = Registry()
    dynamic_field = convert_django_field(Reporter._meta.local_many_to_many[0], registry)
    assert not dynamic_field.get_type()


def test_should_manytomany_convert_connectionorlist_list():
    class A(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = "__all__"

    graphene_field = convert_django_field(
        Reporter._meta.local_many_to_many[0], A._meta.registry
    )
    assert isinstance(graphene_field, graphene.Dynamic)
    dynamic_field = graphene_field.get_type()
    assert isinstance(dynamic_field, graphene.Field)
    # A NonNull List of NonNull A ([A!]!)
    # https://github.com/graphql-python/graphene-django/issues/448
    assert isinstance(dynamic_field.type, NonNull)
    assert isinstance(dynamic_field.type.of_type, graphene.List)
    assert isinstance(dynamic_field.type.of_type.of_type, NonNull)
    assert dynamic_field.type.of_type.of_type.of_type == A


def test_should_manytomany_convert_connectionorlist_connection():
    class A(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    graphene_field = convert_django_field(
        Reporter._meta.local_many_to_many[0], A._meta.registry
    )
    assert isinstance(graphene_field, graphene.Dynamic)
    dynamic_field = graphene_field.get_type()
    assert isinstance(dynamic_field, ConnectionField)
    assert dynamic_field.type.of_type == A._meta.connection


def test_should_manytoone_convert_connectionorlist():
    class A(DjangoObjectType):
        class Meta:
            model = Article
            fields = "__all__"

    graphene_field = convert_django_field(Reporter.articles.rel, A._meta.registry)
    assert isinstance(graphene_field, graphene.Dynamic)
    dynamic_field = graphene_field.get_type()
    assert isinstance(dynamic_field, graphene.Field)
    # a NonNull List of NonNull A ([A!]!)
    assert isinstance(dynamic_field.type, NonNull)
    assert isinstance(dynamic_field.type.of_type, graphene.List)
    assert isinstance(dynamic_field.type.of_type.of_type, NonNull)
    assert dynamic_field.type.of_type.of_type.of_type == A


def test_should_onetoone_reverse_convert_model():
    class A(DjangoObjectType):
        class Meta:
            model = FilmDetails
            fields = "__all__"

    graphene_field = convert_django_field(Film.details.related, A._meta.registry)
    assert isinstance(graphene_field, graphene.Dynamic)
    dynamic_field = graphene_field.get_type()
    assert isinstance(dynamic_field, graphene.Field)
    assert dynamic_field.type == A


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_should_postgres_array_convert_list():
    field = assert_conversion(
        ArrayField, graphene.List, models.CharField(max_length=100)
    )
    assert isinstance(field.type, graphene.NonNull)
    assert isinstance(field.type.of_type, graphene.List)
    assert isinstance(field.type.of_type.of_type, graphene.NonNull)
    assert field.type.of_type.of_type.of_type == graphene.String

    field = assert_conversion(
        ArrayField, graphene.List, models.CharField(max_length=100, null=True)
    )
    assert isinstance(field.type, graphene.NonNull)
    assert isinstance(field.type.of_type, graphene.List)
    assert field.type.of_type.of_type == graphene.String


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_should_postgres_array_multiple_convert_list():
    field = assert_conversion(
        ArrayField, graphene.List, ArrayField(models.CharField(max_length=100))
    )
    assert isinstance(field.type, graphene.NonNull)
    assert isinstance(field.type.of_type, graphene.List)
    assert isinstance(field.type.of_type.of_type, graphene.List)
    assert isinstance(field.type.of_type.of_type.of_type, graphene.NonNull)
    assert field.type.of_type.of_type.of_type.of_type == graphene.String

    field = assert_conversion(
        ArrayField,
        graphene.List,
        ArrayField(models.CharField(max_length=100, null=True)),
    )
    assert isinstance(field.type, graphene.NonNull)
    assert isinstance(field.type.of_type, graphene.List)
    assert isinstance(field.type.of_type.of_type, graphene.List)
    assert field.type.of_type.of_type.of_type == graphene.String


@pytest.mark.skipif(HStoreField is MissingType, reason="HStoreField should exist")
def test_should_postgres_hstore_convert_string():
    assert_conversion(HStoreField, JSONString)


@pytest.mark.skipif(RangeField is MissingType, reason="RangeField should exist")
def test_should_postgres_range_convert_list():
    from django.contrib.postgres.fields import IntegerRangeField

    field = assert_conversion(IntegerRangeField, graphene.List)
    assert isinstance(field.type, graphene.NonNull)
    assert isinstance(field.type.of_type, graphene.List)
    assert isinstance(field.type.of_type.of_type, graphene.NonNull)
    assert field.type.of_type.of_type.of_type == graphene.Int


def test_generate_enum_name():
    MockDjangoModelMeta = namedtuple("DjangoMeta", ["app_label", "object_name"])

    # Simple case
    field = graphene.Field(graphene.String, name="type")
    model_meta = MockDjangoModelMeta(app_label="users", object_name="User")
    assert generate_enum_name(model_meta, field) == "UsersUserTypeChoices"

    # More complicated multiple work case
    field = graphene.Field(graphene.String, name="fizz_buzz")
    model_meta = MockDjangoModelMeta(
        app_label="some_long_app_name", object_name="SomeObject"
    )
    assert (
        generate_enum_name(model_meta, field)
        == "SomeLongAppNameSomeObjectFizzBuzzChoices"
    )


def test_generate_v2_enum_name(graphene_settings):
    MockDjangoModelMeta = namedtuple("DjangoMeta", ["app_label", "object_name"])
    graphene_settings.DJANGO_CHOICE_FIELD_ENUM_V2_NAMING = True

    # Simple case
    field = graphene.Field(graphene.String, name="type")
    model_meta = MockDjangoModelMeta(app_label="users", object_name="User")
    assert generate_enum_name(model_meta, field) == "UserType"

    # More complicated multiple work case
    field = graphene.Field(graphene.String, name="fizz_buzz")
    model_meta = MockDjangoModelMeta(
        app_label="some_long_app_name", object_name="SomeObject"
    )
    assert generate_enum_name(model_meta, field) == "SomeObjectFizzBuzz"


def test_choice_enum_blank_value():
    """Test that choice fields with blank values work"""

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = (
                "first_name",
                "a_choice",
            )

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(root, info):
            return Reporter.objects.first()

    schema = graphene.Schema(query=Query)

    # Create model with empty choice option
    Reporter.objects.create(
        first_name="Bridget", last_name="Jones", email="bridget@example.com"
    )

    result = schema.execute(
        """
        query {
            reporter {
                firstName
                aChoice
            }
        }
    """
    )
    assert not result.errors
    assert result.data == {
        "reporter": {"firstName": "Bridget", "aChoice": None},
    }
