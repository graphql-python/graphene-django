from functools import partial

import six
import graphene
from graphene import Field, Argument
from graphene.types.mutation import MutationMeta
from graphene.types.objecttype import ObjectTypeMeta
from graphene.types.options import Options
from graphene.types.utils import get_field_as, merge
from graphene.utils.is_base_type import is_base_type
from graphene_django.registry import get_global_registry

from .converter import convert_form_to_input_type
from .types import ErrorType


class FormMutationMeta(MutationMeta):
    def __new__(cls, name, bases, attrs):
        if not is_base_type(bases, FormMutationMeta):
            return type.__new__(cls, name, bases, attrs)

        options = Options(
            attrs.pop('Meta', None),
            name=name,
            description=attrs.pop('__doc__', None),
            form_class=None,
            input_field_name='input',
            local_fields=None,
            only_fields=(),
            exclude_fields=(),
            interfaces=(),
            registry=None
        )

        if not options.form_class:
            raise Exception('Missing form_class')

        cls = ObjectTypeMeta.__new__(
            cls, name, bases, dict(attrs, _meta=options)
        )

        options.fields = merge(
            options.interface_fields, options.base_fields, options.local_fields,
            {'errors': get_field_as(cls.errors, Field)}
        )

        cls.Input = convert_form_to_input_type(options.form_class)

        field_kwargs = {options.input_field_name: Argument(cls.Input, required=True)}
        cls.Field = partial(
            Field,
            cls,
            resolver=cls.mutate,
            **field_kwargs
        )

        return cls


class BaseFormMutation(graphene.Mutation):

    @classmethod
    def mutate(cls, root, args, context, info):
        form = cls.get_form(root, args, context, info)

        if form.is_valid():
            return cls.form_valid(form, info)
        else:
            return cls.form_invalid(form, info)

    @classmethod
    def form_valid(cls, form, info):
        form.save()
        return cls(errors=[])

    @classmethod
    def form_invalid(cls, form, info):
        errors = [
            ErrorType(field=key, messages=value)
            for key, value in form.errors.items()
        ]
        return cls(errors=errors)

    @classmethod
    def get_form(cls, root, args, context, info):
        form_data = args.get(cls._meta.input_field_name)
        kwargs = cls.get_form_kwargs(root, args, context, info)
        return cls._meta.form_class(data=form_data, **kwargs)

    @classmethod
    def get_form_kwargs(cls, root, args, context, info):
        return {}


class FormMutation(six.with_metaclass(FormMutationMeta, BaseFormMutation)):

    errors = graphene.List(ErrorType)


class ModelFormMutationMeta(MutationMeta):
    def __new__(cls, name, bases, attrs):
        if not is_base_type(bases, ModelFormMutationMeta):
            return type.__new__(cls, name, bases, attrs)

        options = Options(
            attrs.pop('Meta', None),
            name=name,
            description=attrs.pop('__doc__', None),
            form_class=None,
            input_field_name='input',
            return_field_name=None,
            model=None,
            local_fields=None,
            only_fields=(),
            exclude_fields=(),
            interfaces=(),
            registry=None
        )

        if not options.form_class:
            raise Exception('Missing form_class')

        cls = ObjectTypeMeta.__new__(
            cls, name, bases, dict(attrs, _meta=options)
        )

        options.fields = merge(
            options.interface_fields, options.base_fields, options.local_fields,
            {'errors': get_field_as(cls.errors, Field)}
        )

        cls.Input = convert_form_to_input_type(options.form_class)

        field_kwargs = {options.input_field_name: Argument(cls.Input, required=True)}
        cls.Field = partial(
            Field,
            cls,
            resolver=cls.mutate,
            **field_kwargs
        )

        cls.model = options.model or options.form_class.Meta.model
        cls.return_field_name = cls._meta.return_field_name or cls.model._meta.model_name

        registry = get_global_registry()
        model_type = registry.get_type_for_model(cls.model)

        options.fields[cls.return_field_name] = graphene.Field(model_type)

        return cls


class ModelFormMutation(six.with_metaclass(ModelFormMutationMeta, BaseFormMutation)):

    errors = graphene.List(ErrorType)

    @classmethod
    def form_valid(cls, form, info):
        obj = form.save()
        kwargs = {cls.return_field_name: obj}
        return cls(errors=[], **kwargs)
