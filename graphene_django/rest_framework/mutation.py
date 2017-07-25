from collections import OrderedDict
from functools import partial

import six
import graphene
from graphene import relay
from graphene.types import Argument, Field, InputField
from graphene.types.mutation import Mutation, MutationOptions
from graphene.types.objecttype import (
    yank_fields_from_attrs
)
from graphene.types.options import Options
from graphene.types.utils import get_field_as

from .serializer_converter import (
    convert_serializer_to_input_type,
    convert_serializer_field
)
from .types import ErrorType


class SerializerMutationOptions(MutationOptions):
    serializer_class = None


def fields_for_serializer(serializer, only_fields, exclude_fields):
    fields = OrderedDict()
    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = (
            name in exclude_fields # or
            # name in already_created_fields
        )

        if is_not_in_only or is_excluded:
            continue

        fields[name] = convert_serializer_field(field, is_input=False)
    return fields


class SerializerMutation(relay.ClientIDMutation):
    errors = graphene.List(
        ErrorType,
        description='May contain more than one error for same field.'
    )

    @classmethod
    def __init_subclass_with_meta__(cls, serializer_class, 
        only_fields=(), exclude_fields=(), **options):

        if not serializer_class:
            raise Exception('serializer_class is required for the SerializerMutation')

        serializer = serializer_class()
        serializer_fields = fields_for_serializer(serializer, only_fields, exclude_fields)

        _meta = SerializerMutationOptions(cls)
        _meta.fields = yank_fields_from_attrs(
            serializer_fields,
            _as=Field,
        )

        _meta.input_fields = yank_fields_from_attrs(
            serializer_fields,
            _as=InputField,
        )

    @classmethod
    def mutate(cls, instance, args, request, info):
        input = args.get('input')

        serializer = cls._meta.serializer_class(data=dict(input))

        if serializer.is_valid():
            return cls.perform_mutate(serializer, info)
        else:
            errors = [
                ErrorType(field=key, messages=value)
                for key, value in serializer.errors.items()
            ]

            return cls(errors=errors)

    @classmethod
    def perform_mutate(cls, serializer, info):
        obj = serializer.save()

        return cls(errors=[], **obj)
