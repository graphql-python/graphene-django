import copy

from django import forms
from py.test import raises

import graphene

from ..converter import convert_form_field


def _get_type(form_field, **kwargs):
    # prevents the following error:
    # AssertionError: The `source` argument is not meaningful when applied to a `child=` field.
    # Remove `source=` from the field declaration.
    # since we are reusing the same child in when testing the required attribute

    if 'child' in kwargs:
        kwargs['child'] = copy.deepcopy(kwargs['child'])

    field = form_field(**kwargs)

    return convert_form_field(field)


def assert_conversion(form_field, graphene_field, **kwargs):
    graphene_type = _get_type(form_field, help_text='Custom Help Text', **kwargs)
    assert isinstance(graphene_type, graphene_field)

    graphene_type_required = _get_type(
        form_field, help_text='Custom Help Text', required=True, **kwargs
    )
    assert isinstance(graphene_type_required, graphene_field)

    return graphene_type


def test_should_unknown_form_field_raise_exception():
    with raises(Exception) as excinfo:
        convert_form_field(None)
    assert 'Don\'t know how to convert the form field' in str(excinfo.value)


def test_should_charfield_convert_string():
    assert_conversion(forms.CharField, graphene.String)


def test_should_timefield_convert_time():
    assert_conversion(forms.TimeField, graphene.types.datetime.Time)


def test_should_email_convert_string():
    assert_conversion(forms.EmailField, graphene.String)


def test_should_slug_convert_string():
    assert_conversion(forms.SlugField, graphene.String)


def test_should_url_convert_string():
    assert_conversion(forms.URLField, graphene.String)


def test_should_choicefield_convert_string():
    assert_conversion(forms.ChoiceField, graphene.String, choices=[])


def test_should_regexfield_convert_string():
    assert_conversion(forms.RegexField, graphene.String, regex='[0-9]+')


def test_should_uuidfield_convert_string():
    assert_conversion(forms.UUIDField, graphene.String)


def test_should_integer_convert_int():
    assert_conversion(forms.IntegerField, graphene.Int)


def test_should_boolean_convert_boolean():
    assert_conversion(forms.BooleanField, graphene.Boolean)


def test_should_float_convert_float():
    assert_conversion(forms.FloatField, graphene.Float)


def test_should_decimal_convert_float():
    assert_conversion(forms.DecimalField, graphene.Float, max_digits=4, decimal_places=2)


def test_should_filepath_convert_string():
    assert_conversion(forms.FilePathField, graphene.String, path='/')


def test_should_multiplechoicefield_convert_to_list_of_string():
    field = assert_conversion(forms.MultipleChoiceField, graphene.List, choices=[1, 2, 3])

    assert field.of_type == graphene.String
