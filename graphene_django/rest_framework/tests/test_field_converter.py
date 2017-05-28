from rest_framework import serializers
from py.test import raises

import graphene

from ..serializer_converter import convert_serializer_field


# TODO: test required

def assert_conversion(rest_framework_field, graphene_field, **kwargs):
    field = rest_framework_field(help_text='Custom Help Text', **kwargs)
    graphene_type = convert_serializer_field(field)
    assert isinstance(graphene_type, graphene_field)

    field = graphene_type.Field()
    assert field.description == 'Custom Help Text'
    assert not isinstance(field, graphene.NonNull)

    field = rest_framework_field(help_text='Custom Help Text', required=True, **kwargs)
    graphene_type = convert_serializer_field(field)
    field = graphene_type.Field()
    assert isinstance(field.type, graphene.NonNull)

    return field


def test_should_unknown_rest_framework_field_raise_exception():
    with raises(Exception) as excinfo:
        convert_serializer_field(None)
    assert 'Don\'t know how to convert the serializer field' in str(excinfo.value)


def test_should_date_convert_string():
    assert_conversion(serializers.DateField, graphene.String)


def test_should_time_convert_string():
    assert_conversion(serializers.TimeField, graphene.String)


def test_should_date_time_convert_string():
    assert_conversion(serializers.DateTimeField, graphene.String)


def test_should_char_convert_string():
    assert_conversion(serializers.CharField, graphene.String)


def test_should_email_convert_string():
    assert_conversion(serializers.EmailField, graphene.String)


def test_should_slug_convert_string():
    assert_conversion(serializers.SlugField, graphene.String)


def test_should_url_convert_string():
    assert_conversion(serializers.URLField, graphene.String)


def test_should_choice_convert_string():
    assert_conversion(serializers.ChoiceField, graphene.String, choices=[])


def test_should_base_field_convert_string():
    assert_conversion(serializers.Field, graphene.String)


def test_should_regex_convert_string():
    assert_conversion(serializers.RegexField, graphene.String, regex='[0-9]+')


def test_should_uuid_convert_string():
    if hasattr(serializers, 'UUIDField'):
        assert_conversion(serializers.UUIDField, graphene.String)


def test_should_integer_convert_int():
    assert_conversion(serializers.IntegerField, graphene.Int)


def test_should_boolean_convert_boolean():
    assert_conversion(serializers.BooleanField, graphene.Boolean)


def test_should_float_convert_float():
    assert_conversion(serializers.FloatField, graphene.Float)


def test_should_decimal_convert_float():
    assert_conversion(serializers.DecimalField, graphene.Float, max_digits=4, decimal_places=2)
