import warnings
from collections import OrderedDict
from functools import partial

import six
from django.db.models import Model
from django.utils.functional import SimpleLazyObject

import graphene
from graphene import Field, NonNull
from graphene.relay import Connection, Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_camel_case

from graphene_django.utils.utils import auth_resolver
from .converter import convert_django_field_with_choices
from .registry import Registry, get_global_registry
from .settings import graphene_settings
from .utils import (
    DJANGO_FILTER_INSTALLED,
    get_model_fields,
    is_valid_django_model,
)

if six.PY3:
    from typing import Type

ALL_FIELDS = "__all__"


def construct_fields(
    model, registry, only_fields, exclude_fields, convert_choices_to_enum
):
    _model_fields = get_model_fields(model)

    fields = OrderedDict()
    for name, field in _model_fields:
        is_not_in_only = only_fields and name not in only_fields
        # is_already_created = name in options.fields
        is_excluded = name in exclude_fields  # or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith("+")
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue

        _convert_choices_to_enum = convert_choices_to_enum
        if not isinstance(_convert_choices_to_enum, bool):
            # then `convert_choices_to_enum` is a list of field names to convert
            if name in _convert_choices_to_enum:
                _convert_choices_to_enum = True
            else:
                _convert_choices_to_enum = False

        converted = convert_django_field_with_choices(
            field, registry, convert_choices_to_enum=_convert_choices_to_enum
        )
        fields[name] = converted

    return fields


def validate_fields(type_, model, fields, only_fields, exclude_fields):
    # Validate the given fields against the model's fields and custom fields
    all_field_names = set(fields.keys())
    for name in only_fields or ():
        if name in all_field_names:
            continue

        if hasattr(model, name):
            warnings.warn(
                (
                    'Field name "{field_name}" matches an attribute on Django model "{app_label}.{object_name}" '
                    "but it's not a model field so Graphene cannot determine what type it should be. "
                    'Either define the type of the field on DjangoObjectType "{type_}" or remove it from the "fields" '
                    "list. "
                ).format(
                    field_name=name,
                    app_label=model._meta.app_label,
                    object_name=model._meta.object_name,
                    type_=type_,
                )
            )

        else:
            warnings.warn(
                (
                    'Field name "{field_name}" doesn\'t exist on Django model "{app_label}.{object_name}". '
                    'Consider removing the field from the "fields" list of DjangoObjectType "{type_}" because it has '
                    "no effect. "
                ).format(
                    field_name=name,
                    app_label=model._meta.app_label,
                    object_name=model._meta.object_name,
                    type_=type_,
                )
            )

    # Validate exclude fields
    for name in exclude_fields or ():
        if name in all_field_names:
            # Field is a custom field
            warnings.warn(
                (
                    'Excluding the custom field "{field_name}" on DjangoObjectType "{type_}" has no effect. '
                    'Either remove the custom field or remove the field from the "exclude" list.'
                ).format(
                    field_name=name,
                    app_label=model._meta.app_label,
                    object_name=model._meta.object_name,
                    type_=type_,
                )
            )
        else:
            if not hasattr(model, name):
                warnings.warn(
                    (
                        'Django model "{app_label}.{object_name}" does not have a field or attribute named "{'
                        'field_name}". '
                        'Consider removing the field from the "exclude" list of DjangoObjectType "{type_}" because it '
                        "has no effect "
                    ).format(
                        field_name=name,
                        app_label=model._meta.app_label,
                        object_name=model._meta.object_name,
                        type_=type_,
                    )
                )


def get_auth_resolver(
    name, permissions, resolver=None, raise_exception=False, permission_classes=None
):
    """
    Get middleware resolver to handle field permissions
    :param name: Field name
    :param permissions: List of permissions
    :param resolver: Field resolver
    :param raise_exception: If True a PermissionDenied is raised
    :param permission_classes: Permission for user
    :return: Middleware resolver to check permissions
    """
    return partial(
        auth_resolver,
        resolver,
        permissions,
        name,
        None,
        raise_exception,
        permission_classes=permission_classes,
    )


class DjangoObjectTypeOptions(ObjectTypeOptions):
    model = None  # type: Model
    registry = None  # type: Registry
    connection = None  # type: Type[Connection]

    filter_fields = ()
    filterset_class = None


class DjangoObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        registry=None,
        skip_registry=False,
        only_fields=(),  # deprecated in favour of `fields`
        fields=(),
        exclude_fields=(),  # deprecated in favour of `exclude`
        exclude=(),
        filter_fields=None,
        filterset_class=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        convert_choices_to_enum=True,
        field_to_permission=None,
        permission_to_field=None,
        permission_to_all_fields=None,
        permission_raise_exception=True,
        _meta=None,
        **options
    ):
        assert is_valid_django_model(model), (
            'You need to pass a valid Django Model in {}.Meta, received "{}".'
        ).format(cls.__name__, model)

        if not registry:
            registry = get_global_registry()

        assert isinstance(registry, Registry), (
            "The attribute registry in {} needs to be an instance of "
            'Registry, received "{}".'
        ).format(cls.__name__, registry)

        if filter_fields and filterset_class:
            raise Exception("Can't set both filter_fields and filterset_class")

        if not DJANGO_FILTER_INSTALLED and (filter_fields or filterset_class):
            raise Exception(
                (
                    "Can only set filter_fields or filterset_class if "
                    "Django-Filter is installed"
                )
            )

        assert not (fields and exclude), (
            "Cannot set both 'fields' and 'exclude' options on "
            "DjangoObjectType {class_name}.".format(class_name=cls.__name__)
        )

        # Alias only_fields -> fields
        if only_fields and fields:
            raise Exception("Can't set both only_fields and fields")
        if only_fields:
            warnings.warn(
                "Defining `only_fields` is deprecated in favour of `fields`.",
                PendingDeprecationWarning,
                stacklevel=2,
            )
            fields = only_fields
        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". '
                "Got %s." % type(fields).__name__
            )

        if fields == ALL_FIELDS:
            fields = None

        # Alias exclude_fields -> exclude
        if exclude_fields and exclude:
            raise Exception("Can't set both exclude_fields and exclude")
        if exclude_fields:
            warnings.warn(
                "Defining `exclude_fields` is deprecated in favour of `exclude`.",
                PendingDeprecationWarning,
                stacklevel=2,
            )
            exclude = exclude_fields
        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError(
                "The `exclude` option must be a list or tuple. Got %s."
                % type(exclude).__name__
            )

        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, fields, exclude, convert_choices_to_enum),
            _as=Field,
        )

        if use_connection is None and interfaces:
            use_connection = any(
                (issubclass(interface, Node) for interface in interfaces)
            )

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = Connection

            connection = connection_class.create_type(
                "{}Connection".format(cls.__name__), node=cls
            )

        if connection is not None:
            assert issubclass(connection, Connection), (
                "The connection must be a Connection. Received {}"
            ).format(connection.__name__)

        if not _meta:
            _meta = DjangoObjectTypeOptions(cls)

        _meta.model = model
        _meta.registry = registry
        _meta.filter_fields = filter_fields
        _meta.filterset_class = filterset_class
        _meta.fields = django_fields
        _meta.connection = connection

        permission_classes = getattr(cls, "permission_classes", None)

        super(DjangoObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        field_permissions, fields_raise_exception = cls.__get_field_permissions__(
            field_to_permission,
            permission_to_field,
            permission_to_all_fields,
            permission_classes,
            permission_raise_exception,
        )

        # Validate fields
        validate_fields(cls, model, _meta.fields, fields, exclude)

        if field_permissions:
            cls.__set_permissions_resolvers__(
                field_permissions, fields_raise_exception, permission_classes
            )

        cls.field_permissions = field_permissions

        if not skip_registry:
            registry.register(cls)

    @classmethod
    def __get_field_permissions__(
        cls,
        field_to_permission,
        permission_to_field,
        permission_to_all_fields,
        permission_classes,
        permission_raise_exception,
    ):
        """Combines permissions from meta"""
        permissions = field_to_permission if field_to_permission else {}
        perm_to_field = cls.__get_permission_to_fields__(
            permission_to_field if permission_to_field else {}
        )
        fields_raise_exception = {}

        for name, field in cls._meta.fields.items():
            if name == "id":
                continue

            if permission_classes:
                permissions[name] = ()

            if name in perm_to_field:
                if name in permissions:
                    permissions[name] += perm_to_field[name]
                else:
                    permissions[name] = perm_to_field[name]

            if permission_to_all_fields:
                permissions[name] = tuple(
                    set(permissions.get(name, ()) + permission_to_all_fields)
                )

            if name in permissions and permission_raise_exception:
                fields_raise_exception[name] = hasattr(field, "_type") and isinstance(
                    field._type, NonNull
                )

        return permissions, fields_raise_exception

    @classmethod
    def __get_permission_to_fields__(cls, permission_to_field):
        """
        Accepts a dictionary like
            {
                permission: [fields]
            }
        :return: Mapping of fields to permissions like
            {
                field: [permissions]
            }
        """
        permissions = {}
        for permission, fields in permission_to_field.items():
            for field in fields:
                permissions[field] = permissions.get(field, ()) + (permission,)
        return permissions

    @classmethod
    def __set_permissions_resolvers__(
        cls, permissions, fields_raise_exception, permission_classes
    ):
        """Set permission resolvers"""
        for field_name, field_permissions in permissions.items():
            raise_exception = fields_raise_exception.get(field_name, False)
            attr = "resolve_{}".format(field_name)
            resolver = getattr(
                cls._meta.fields[field_name], "resolver", None
            ) or getattr(cls, attr, None)

            if not resolver:

                for interface in cls._meta.interfaces:

                    resolver = getattr(
                        interface._meta.fields.get(field_name, None), "resolver", None
                    ) or getattr(interface, attr, None)

                    if resolver:
                        break

            if not hasattr(field_permissions, "__iter__"):
                field_permissions = tuple(field_permissions)

            setattr(
                cls,
                attr,
                get_auth_resolver(
                    field_name,
                    field_permissions,
                    resolver,
                    raise_exception,
                    permission_classes,
                ),
            )

    @classmethod
    def __set_as_nullable__(cls, field_permissions, model, registry):
        """Set restricted fields as nullable"""
        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, field_permissions.keys(), (), True),
            _as=Field,
        )
        for name, field in django_fields.items():
            if hasattr(field, "_type") and isinstance(field._type, NonNull):
                field._type = field._type._of_type
                setattr(cls, name, field)

    def resolve_id(self, info):
        return self.pk

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, SimpleLazyObject):
            root._setup()
            root = root._wrapped
        if isinstance(root, cls):
            return True
        if not is_valid_django_model(type(root)):
            raise Exception(('Received incompatible instance "{}".').format(root))

        if cls._meta.model._meta.proxy:
            model = root._meta.model
        else:
            model = root._meta.model._meta.concrete_model

        return model == cls._meta.model

    @classmethod
    def get_queryset(cls, queryset, info):
        return queryset

    @classmethod
    def get_node(cls, info, id):
        queryset = cls.get_queryset(cls._meta.model.objects, info)
        try:
            return queryset.get(pk=id)
        except cls._meta.model.DoesNotExist:
            return None


class ErrorType(ObjectType):
    field = graphene.String(required=True)
    messages = graphene.List(graphene.NonNull(graphene.String), required=True)

    @classmethod
    def from_errors(cls, errors):
        data = {
            to_camel_case(key)
            if key != "__all__" and graphene_settings.CAMELCASE_ERRORS
            else key: value
            for key, value in errors.items()
        }
        return [cls(field=key, messages=value) for key, value in data.items()]
