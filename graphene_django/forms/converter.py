from django import forms
from django.core.exceptions import ImproperlyConfigured
from graphene_django.utils import import_single_dispatch
import graphene


singledispatch = import_single_dispatch()


def convert_form_to_input_type(form_class):
    form = form_class()

    items = {
        name: convert_form_field(field)
        for name, field in form.fields.items()
    }

    return type(
        '{}Input'.format(form.__class__.__name__),
        (graphene.InputObjectType, ),
        items
    )


@singledispatch
def get_graphene_type_from_form_field(field):
    raise ImproperlyConfigured(
        "Don't know how to convert the form field %s (%s) "
        "to Graphene type" % (field, field.__class__)
    )


def convert_form_field(field, is_input=True):
    """
    Converts a Django form field to a graphql field and marks the field as
    required if we are creating an input type and the field itself is required
    """

    graphql_type = get_graphene_type_from_form_field(field)

    kwargs = {
        'description': field.help_text,
        'required': is_input and field.required,
    }

    # if it is a tuple or a list it means that we are returning
    # the graphql type and the child type
    if isinstance(graphql_type, (list, tuple)):
        kwargs['of_type'] = graphql_type[1]
        graphql_type = graphql_type[0]

    return graphql_type(**kwargs)


@get_graphene_type_from_form_field.register(forms.CharField)
@get_graphene_type_from_form_field.register(forms.ChoiceField)
def convert_form_field_to_string(field):
    return graphene.String


@get_graphene_type_from_form_field.register(forms.IntegerField)
def convert_form_field_to_int(field):
    return graphene.Int


@get_graphene_type_from_form_field.register(forms.BooleanField)
def convert_form_field_to_bool(field):
    return graphene.Boolean


@get_graphene_type_from_form_field.register(forms.FloatField)
@get_graphene_type_from_form_field.register(forms.DecimalField)
def convert_form_field_to_float(field):
    return graphene.Float


@get_graphene_type_from_form_field.register(forms.DateField)
@get_graphene_type_from_form_field.register(forms.DateTimeField)
def convert_form_field_to_datetime(field):
    return graphene.types.datetime.DateTime


@get_graphene_type_from_form_field.register(forms.TimeField)
def convert_form_field_to_time(field):
    return graphene.types.datetime.Time


@get_graphene_type_from_form_field.register(forms.MultipleChoiceField)
def convert_form_field_to_list_of_string(field):
    return (graphene.List, graphene.String)
