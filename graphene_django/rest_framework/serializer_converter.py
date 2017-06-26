from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers

import graphene

from ..utils import import_single_dispatch

singledispatch = import_single_dispatch()


def convert_serializer_to_input_type(serializer_class):
    serializer = serializer_class()

    items = {
        name: convert_serializer_field(field)
        for name, field in serializer.fields.items()
    }

    return type(
        '{}Input'.format(serializer.__class__.__name__),
        (graphene.InputObjectType, ),
        items
    )


@singledispatch
def get_graphene_type_from_serializer_field(field):
    raise ImproperlyConfigured(
        "Don't know how to convert the serializer field %s (%s) "
        "to Graphene type" % (field, field.__class__)
    )


def convert_serializer_field(field, is_input=True):
    """
    Converts a django rest frameworks field to a graphql field
    and marks the field as required if we are creating an input type
    and the field itself is required
    """

    # TODO: sub types? kwargs

    graphql_type = get_graphene_type_from_serializer_field(field)

    return graphql_type(
        description=field.help_text, required=is_input and field.required
    )


@get_graphene_type_from_serializer_field.register(serializers.Field)
def convert_serializer_field_to_string(field):
    return graphene.String


@get_graphene_type_from_serializer_field.register(serializers.IntegerField)
def convert_serializer_field_to_int(field):
    return graphene.Int


@get_graphene_type_from_serializer_field.register(serializers.BooleanField)
def convert_serializer_field_to_bool(field):
    return graphene.Boolean


@get_graphene_type_from_serializer_field.register(serializers.FloatField)
@get_graphene_type_from_serializer_field.register(serializers.DecimalField)
def convert_serializer_field_to_float(field):
    return graphene.Float
