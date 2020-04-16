from django import forms
from django.core.exceptions import ImproperlyConfigured

from graphene import (
    ID,
    Boolean,
    Float,
    Int,
    List,
    String,
    UUID,
    Date,
    DateTime,
    Time,
    Enum,
)
from graphene.utils.str_converters import to_camel_case

from graphene_django.converter import get_choices
from .forms import GlobalIDFormField, GlobalIDMultipleChoiceField
from ..utils import import_single_dispatch

singledispatch = import_single_dispatch()


@singledispatch
def convert_form_field(field):
    raise ImproperlyConfigured(
        "Don't know how to convert the Django form field %s (%s) "
        "to Graphene type" % (field, field.__class__)
    )


@convert_form_field.register(forms.fields.BaseTemporalField)
@convert_form_field.register(forms.CharField)
@convert_form_field.register(forms.EmailField)
@convert_form_field.register(forms.SlugField)
@convert_form_field.register(forms.URLField)
@convert_form_field.register(forms.ChoiceField)
@convert_form_field.register(forms.RegexField)
@convert_form_field.register(forms.Field)
def convert_form_field_to_string(field):
    return String(description=field.help_text, required=field.required)


@convert_form_field.register(forms.UUIDField)
def convert_form_field_to_uuid(field):
    return UUID(description=field.help_text, required=field.required)


@convert_form_field.register(forms.IntegerField)
@convert_form_field.register(forms.NumberInput)
def convert_form_field_to_int(field):
    return Int(description=field.help_text, required=field.required)


@convert_form_field.register(forms.BooleanField)
def convert_form_field_to_boolean(field):
    return Boolean(description=field.help_text, required=field.required)


@convert_form_field.register(forms.NullBooleanField)
def convert_form_field_to_nullboolean(field):
    return Boolean(description=field.help_text)


@convert_form_field.register(forms.DecimalField)
@convert_form_field.register(forms.FloatField)
def convert_form_field_to_float(field):
    return Float(description=field.help_text, required=field.required)


@convert_form_field.register(forms.ModelMultipleChoiceField)
@convert_form_field.register(GlobalIDMultipleChoiceField)
def convert_form_field_to_list(field):
    return List(ID, required=field.required)


@convert_form_field.register(forms.DateField)
def convert_form_field_to_date(field):
    return Date(description=field.help_text, required=field.required)


@convert_form_field.register(forms.DateTimeField)
def convert_form_field_to_datetime(field):
    return DateTime(description=field.help_text, required=field.required)


@convert_form_field.register(forms.TimeField)
def convert_form_field_to_time(field):
    return Time(description=field.help_text, required=field.required)


@convert_form_field.register(forms.ModelChoiceField)
@convert_form_field.register(GlobalIDFormField)
def convert_form_field_to_id(field):
    return ID(required=field.required)


def get_form_name(form):
    """Get form name"""
    class_name = str(form.__class__).split(".")[-1]
    return class_name[:-2]


def convert_form_field_with_choices(field, name=None, form=None):
    """
    Helper method to convert a field to graphene Field type.
    :param name: form field's name
    :param field: form field to convert to
    :param form: field's form
    :return: graphene Field
    """
    choices = getattr(field, "choices", None)

    # If is a choice field, but not depends on models
    if (
        not isinstance(field, (forms.ModelMultipleChoiceField, forms.ModelChoiceField))
        and choices
    ):
        if form:
            name = to_camel_case(
                "{}_{}".format(get_form_name(form), field.label or name)
            )
        else:
            name = field.label or name
        name = to_camel_case(name.replace(" ", "_"))
        choices = list(get_choices(choices))
        named_choices = [(c[0], c[1]) for c in choices]
        named_choices_descriptions = {c[0]: c[2] for c in choices}

        class EnumWithDescriptionsType(object):
            """Enum type definition"""

            @property
            def description(self):
                """Return field description"""

                return named_choices_descriptions[self.name]

        enum = Enum(name, list(named_choices), type=EnumWithDescriptionsType)
        return enum(
            description=field.help_text, required=field.required
        )  # pylint: disable=E1102
    return convert_form_field(field)
