from functools import singledispatch

from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers

import graphene


@singledispatch
def convert_serializer_field(field):
    raise ImproperlyConfigured(
        "Don't know how to convert the serializer field %s (%s) "
        "to Graphene type" % (field, field.__class__)
    )


def required_if_input_and_required(func):
    """
    Marks the field as required if we are creating an input type
    and the field itself is required
    """

    def wrap(field, is_input=True):
        graphql_type = func(field)

        return graphql_type(
            description=field.help_text, required=is_input and field.required
        )

    return wrap


@convert_serializer_field.register(serializers.Field)
@required_if_input_and_required
def convert_serializer_field_to_string(field):
    return graphene.String


@convert_serializer_field.register(serializers.IntegerField)
@required_if_input_and_required
def convert_serializer_field_to_int(field):
    return graphene.Int


@convert_serializer_field.register(serializers.BooleanField)
@required_if_input_and_required
def convert_serializer_field_to_bool(field):
    return graphene.Boolean


@convert_serializer_field.register(serializers.FloatField)
@convert_serializer_field.register(serializers.DecimalField)
@required_if_input_and_required
def convert_serializer_field_to_float(field):
    return graphene.Float


