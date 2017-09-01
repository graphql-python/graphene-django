from collections import OrderedDict

import graphene
from graphene.types import Field, InputField
from graphene.types.mutation import MutationOptions
from graphene.relay.mutation import ClientIDMutation
from graphene.types.objecttype import (
    yank_fields_from_attrs
)

from .serializer_converter import (
    convert_serializer_field
)
from .types import ErrorType


class SerializerMutationOptions(MutationOptions):
    serializer_class = None


def fields_for_serializer(serializer, only_fields, exclude_fields, is_input=False):
    fields = OrderedDict()
    for name, field in serializer.fields.items():
        is_not_in_only = only_fields and name not in only_fields
        is_excluded = (
            name in exclude_fields  # or
            # name in already_created_fields
        )

        if is_not_in_only or is_excluded:
            continue

        fields[name] = convert_serializer_field(field, is_input=is_input)
    return fields


class SerializerMutation(ClientIDMutation):
    class Meta:
        abstract = True

    errors = graphene.List(
        ErrorType,
        description='May contain more than one error for same field.'
    )

    @classmethod
    def __init_subclass_with_meta__(cls, serializer_class=None,
                                    only_fields=(), exclude_fields=(), **options):

        if not serializer_class:
            raise Exception('serializer_class is required for the SerializerMutation')

        serializer = serializer_class()
        input_fields = fields_for_serializer(serializer, only_fields, exclude_fields, is_input=True)
        output_fields = fields_for_serializer(serializer, only_fields, exclude_fields, is_input=False)

        _meta = SerializerMutationOptions(cls)
        _meta.serializer_class = serializer_class
        _meta.fields = yank_fields_from_attrs(
            output_fields,
            _as=Field,
        )

        input_fields = yank_fields_from_attrs(
            input_fields,
            _as=InputField,
        )
        super(SerializerMutation, cls).__init_subclass_with_meta__(_meta=_meta, input_fields=input_fields, **options)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        serializer = cls._meta.serializer_class(data=input)

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
        return cls(errors=None, **obj)
