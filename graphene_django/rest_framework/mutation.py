from collections import OrderedDict
from functools import partial

import six
import graphene
from graphene.types import Argument, Field
from graphene.types.mutation import Mutation, MutationMeta
from graphene.types.objecttype import (
    ObjectTypeMeta,
    merge,
    yank_fields_from_attrs
)
from graphene.types.options import Options
from graphene.types.utils import get_field_as
from graphene.utils.is_base_type import is_base_type

from .serializer_converter import (
    convert_serializer_to_input_type,
    convert_serializer_field
)
from .types import ErrorType


class SerializerMutationOptions(Options):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, serializer_class=None, **kwargs)


class SerializerMutationMeta(MutationMeta):
    def __new__(cls, name, bases, attrs):
        if not is_base_type(bases, SerializerMutationMeta):
            return type.__new__(cls, name, bases, attrs)

        options = Options(
            attrs.pop('Meta', None),
            name=name,
            description=attrs.pop('__doc__', None),
            serializer_class=None,
            local_fields=None,
            only_fields=(),
            exclude_fields=(),
            interfaces=(),
            registry=None
        )

        if not options.serializer_class:
            raise Exception('Missing serializer_class')

        cls = ObjectTypeMeta.__new__(
            cls, name, bases, dict(attrs, _meta=options)
        )

        serializer_fields = cls.fields_for_serializer(options)
        options.serializer_fields = yank_fields_from_attrs(
            serializer_fields,
            _as=Field,
        )

        options.fields = merge(
            options.interface_fields, options.serializer_fields,
            options.base_fields, options.local_fields,
            {'errors': get_field_as(cls.errors, Field)}
        )

        cls.Input = convert_serializer_to_input_type(options.serializer_class)

        cls.Field = partial(
            Field,
            cls,
            resolver=cls.mutate,
            input=Argument(cls.Input, required=True)
        )

        return cls

    @staticmethod
    def fields_for_serializer(options):
        serializer = options.serializer_class()

        only_fields = options.only_fields

        already_created_fields = {
            name
            for name, _ in options.local_fields.items()
        }

        fields = OrderedDict()
        for name, field in serializer.fields.items():
            is_not_in_only = only_fields and name not in only_fields
            is_excluded = (
                name in options.exclude_fields or
                name in already_created_fields
            )

            if is_not_in_only or is_excluded:
                continue

            fields[name] = convert_serializer_field(field, is_input=False)
        return fields


class SerializerMutation(six.with_metaclass(SerializerMutationMeta, Mutation)):
    errors = graphene.List(
        ErrorType,
        description='May contain more than one error for '
        'same field.'
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
