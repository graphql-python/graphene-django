from collections import OrderedDict

import six

from django.utils.functional import SimpleLazyObject
from graphene import Field, ObjectType
from graphene.types.objecttype import ObjectTypeMeta
from graphene.types.options import Options
from graphene.types.utils import merge, yank_fields_from_attrs
from graphene.utils.is_base_type import is_base_type

from .converter import convert_django_field_with_choices
from .registry import Registry, get_global_registry
from .utils import (DJANGO_FILTER_INSTALLED, get_model_fields,
                    is_valid_django_model)


def construct_fields(options):
    _model_fields = get_model_fields(options)
    only_fields = options.only_fields
    exclude_fields = options.exclude_fields

    fields = OrderedDict()
    for field in _model_fields:
        name = field.name
        is_not_in_only = only_fields and name not in options.only_fields
        is_already_created = name in options.fields
        is_excluded = name in exclude_fields or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith('+')
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue
        converted = convert_django_field_with_choices(field, options.registry)
        if not converted:
            continue
        fields[name] = converted

    return fields


class DjangoObjectTypeMeta(ObjectTypeMeta):

    @staticmethod
    def __new__(cls, name, bases, attrs):
        # Also ensure initialization is only performed for subclasses of
        # DjangoObjectType
        if not is_base_type(bases, DjangoObjectTypeMeta):
            return type.__new__(cls, name, bases, attrs)

        defaults = dict(
            name=name,
            description=attrs.pop('__doc__', None),
            model=None,
            reverse_fields=True,
            local_fields=None,
            only_fields=(),
            exclude_fields=(),
            interfaces=(),
            registry=None
        )
        if DJANGO_FILTER_INSTALLED:
            # In case Django filter is available, then
            # we allow more attributes in Meta
            defaults.update(
                filter_fields=(),
            )

        options = Options(
            attrs.pop('Meta', None),
            **defaults
        )
        if not options.registry:
            options.registry = get_global_registry()
        assert isinstance(options.registry, Registry), (
            'The attribute registry in {}.Meta needs to be an instance of '
            'Registry, received "{}".'
        ).format(name, options.registry)
        assert is_valid_django_model(options.model), (
            'You need to pass a valid Django Model in {}.Meta, received "{}".'
        ).format(name, options.model)

        cls = ObjectTypeMeta.__new__(cls, name, bases, dict(attrs, _meta=options))

        options.registry.register(cls)

        options.django_fields = yank_fields_from_attrs(
            construct_fields(options),
            _as=Field,
        )
        options.fields = merge(
            options.interface_fields,
            options.django_fields,
            options.base_fields,
            options.local_fields
        )

        return cls


class DjangoObjectType(six.with_metaclass(DjangoObjectTypeMeta, ObjectType)):

    def resolve_id(self, args, context, info):
        return self.pk

    @classmethod
    def is_type_of(cls, root, context, info):
        if isinstance(root, SimpleLazyObject):
            root._setup()
            root = root._wrapped
        if isinstance(root, cls):
            return True
        if not is_valid_django_model(type(root)):
            raise Exception((
                'Received incompatible instance "{}".'
            ).format(root))
        model = root._meta.model
        return model == cls._meta.model

    @classmethod
    def get_node(cls, id, context, info):
        try:
            return cls._meta.model.objects.get(pk=id)
        except cls._meta.model.DoesNotExist:
            return None
