from collections import OrderedDict
from functools import partial

from django.utils.functional import SimpleLazyObject
from graphene import Field, NonNull
from graphene.relay import Connection, Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs

from .converter import convert_django_field_with_choices
from .registry import Registry, get_global_registry
from .utils import DJANGO_FILTER_INSTALLED, get_model_fields, is_valid_django_model, auth_resolver


def construct_fields(model, registry, only_fields, exclude_fields):
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
        converted = convert_django_field_with_choices(field, registry)
        fields[name] = converted

    return fields


class DjangoObjectTypeOptions(ObjectTypeOptions):
    model = None  # type: Model
    registry = None  # type: Registry
    connection = None  # type: Type[Connection]

    filter_fields = ()


class DjangoObjectType(ObjectType):
    """
    DjangoObjectType inheritance to handle field authorization
    Accepts field's permissions description as:

    class Meta:

        field_to_permission = {
            'restricted_field': ('permission1', 'permission2')
        }

        permission_to_field = {
            'permission': ('restricted_field_1', 'restricted_field_2')
        }

    At least one of the permissions must be accomplished in order to resolve the field.
    """
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        registry=None,
        skip_registry=False,
        only_fields=(),
        exclude_fields=(),
        filter_fields=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        field_to_permission=None,
        permission_to_field=None,
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

        if not DJANGO_FILTER_INSTALLED and filter_fields:
            raise Exception("Can only set filter_fields if Django-Filter is installed")

        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, only_fields, exclude_fields), _as=Field
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
        _meta.fields = django_fields
        _meta.connection = connection

        super(DjangoObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        if cls.field_permissions:
            cls.__set_as_nullable__(cls._meta.model, cls._meta.registry)

        if not skip_registry:
            registry.register(cls)

    @classmethod
    def __set_permissions__(cls, field_to_permission, permission_to_field):
        """Combines permissions from meta"""
        permissions = field_to_permission if field_to_permission else {}
        if permission_to_field:
            perm_to_field = cls.__get_permission_to_fields__(permission_to_field)
            for field, perms in perm_to_field.items():
                if field in permissions:
                    permissions[field] += perms
                else:
                    permissions[field] = perms

        cls.field_permissions = permissions

        for field_name, field_permissions in permissions.items():
            attr = 'resolve_{}'.format(field_name)
            resolver = getattr(cls._meta.fields[field_name], 'resolver', None) or getattr(cls, attr, None)

            if not hasattr(field_permissions, '__iter__'):
                field_permissions = tuple(field_permissions)

            setattr(cls, attr, cls.set_auth_resolver(field_name, field_permissions, resolver))

    @classmethod
    def __set_as_nullable__(cls, model, registry):
        """Set restricted fields as nullable"""
        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, cls.field_permissions.keys(), ()),
            _as=Field,
        )
        for name, field in django_fields.items():
            if hasattr(field, '_type') and isinstance(field._type, NonNull):
                field._type = field._type._of_type
                setattr(cls, name, field)

    @classmethod
    def __get_permission_to_fields__(cls, permission_to_field):
        """
        Accepts a dictionary like
            {
                permission: [fields]
            }
        :return: Mapping of fields to permissions
        """
        permissions = {}
        for permission, fields in permission_to_field.items():
            for field in fields:
                permissions[field] = permissions.get(field, ()) + (permission,)
        return permissions

    @classmethod
    def set_auth_resolver(cls, name, permissions, resolver=None):
        """
        Set middleware resolver to handle field permissions
        :param name: Field name
        :param permissions: List of permissions
        :param field: Meta's field
        :param resolver: Field resolver
        :return: Middleware resolver to check permissions
        """
        return partial(auth_resolver, resolver, permissions, name, None, False)

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

        model = root._meta.model._meta.concrete_model
        return model == cls._meta.model

    @classmethod
    def get_node(cls, info, id):
        try:
            return cls._meta.model.objects.get(pk=id)
        except cls._meta.model.DoesNotExist:
            return None
