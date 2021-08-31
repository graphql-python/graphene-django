import warnings
from collections import OrderedDict
from copy import deepcopy
from typing import Type

from django.db.models import Model, Prefetch, QuerySet

import graphene
from graphene.relay import Connection, Node
from graphene.types import Dynamic
from graphene.types.mountedtype import MountedType
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.unmountedtype import UnmountedType
from graphene.types.utils import yank_fields_from_attrs
from graphene.utils.str_converters import to_snake_case

from .converter import convert_django_field_with_choices
from .registry import Registry, get_global_registry
from .settings import graphene_settings
from .utils import (
    DJANGO_FILTER_INSTALLED,
    camelize,
    get_model_fields,
    is_valid_django_model,
)

ALL_FIELDS = "__all__"


def construct_fields(
    model, registry, only_fields, exclude_fields, convert_choices_to_enum
):
    _model_fields = get_model_fields(model)

    fields = OrderedDict()
    for name, field in _model_fields:
        is_not_in_only = (
            only_fields is not None
            and only_fields != ALL_FIELDS
            and name not in only_fields
        )
        # is_already_created = name in options.fields
        is_excluded = (
            exclude_fields is not None and name in exclude_fields
        )  # or is_already_created
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
    only_fields = only_fields if only_fields is not ALL_FIELDS else ()
    for name in only_fields or ():
        if name in all_field_names:
            continue

        if hasattr(model, name):
            warnings.warn(
                (
                    'Field name "{field_name}" matches an attribute on Django model "{app_label}.{object_name}" '
                    "but it's not a model field so Graphene cannot determine what type it should be. "
                    'Either define the type of the field on DjangoObjectType "{type_}" or remove it from the "fields" list.'
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
                    'Consider removing the field from the "fields" list of DjangoObjectType "{type_}" because it has no effect.'
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
                ).format(field_name=name, type_=type_)
            )
        else:
            if not hasattr(model, name):
                warnings.warn(
                    (
                        'Django model "{app_label}.{object_name}" does not have a field or attribute named "{field_name}". '
                        'Consider removing the field from the "exclude" list of DjangoObjectType "{type_}" because it has no effect'
                    ).format(
                        field_name=name,
                        app_label=model._meta.app_label,
                        object_name=model._meta.object_name,
                        type_=type_,
                    )
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
        only_fields=None,  # deprecated in favour of `fields`
        fields=None,
        exclude_fields=None,  # deprecated in favour of `exclude`
        exclude=None,
        filter_fields=None,
        filterset_class=None,
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        convert_choices_to_enum=True,
        _meta=None,
        **options
    ):

        # ---- < Fernnado Code > ----
        cls._preparation_functions_by_field = {}
        cls.register_every_qs_preparation()
        cls.register_meta_fields(model, fields)
        cls.register_attr_fields()
        # ---- </ Fernnado Code > ----

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
                DeprecationWarning,
                stacklevel=2,
            )
            fields = only_fields
        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". '
                "Got %s." % type(fields).__name__
            )

        # Alias exclude_fields -> exclude
        if exclude_fields and exclude:
            raise Exception("Can't set both exclude_fields and exclude")
        if exclude_fields:
            warnings.warn(
                "Defining `exclude_fields` is deprecated in favour of `exclude`.",
                DeprecationWarning,
                stacklevel=2,
            )
            exclude = exclude_fields
        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError(
                "The `exclude` option must be a list or tuple. Got %s."
                % type(exclude).__name__
            )

        if fields is None and exclude is None:
            warnings.warn(
                "Creating a DjangoObjectType without either the `fields` "
                "or the `exclude` option is deprecated. Add an explicit `fields "
                "= '__all__'` option on DjangoObjectType {class_name} to use all "
                "fields".format(class_name=cls.__name__,),
                DeprecationWarning,
                stacklevel=2,
            )

        django_fields = yank_fields_from_attrs(
            construct_fields(model, registry, fields, exclude, convert_choices_to_enum),
            _as=graphene.Field,
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
                "{}Connection".format(options.get("name") or cls.__name__), node=cls
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

        super(DjangoObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        # Validate fields
        validate_fields(cls, model, _meta.fields, fields, exclude)

        if not skip_registry:
            registry.register(cls)

    def resolve_id(self, info):
        return self.pk

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, cls):
            return True
        if not is_valid_django_model(root.__class__):
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



    # ---- < Fernando Code > ----

    @staticmethod
    def convert_model_field_to_graphene_type(model_field):
        graphene_field = convert_django_field_with_choices(model_field, registry=get_global_registry())
        return deepcopy(graphene_field)

    @classmethod
    def prepare(cls, value, selection, info):
        if not isinstance(value, (Model, QuerySet,)):
            return value # If value is not a qs, it cannot be prepared

        if isinstance(value, Model):
            should_return_model_instance = True
            queryset = type(value._setupfunc()).objects.filter(pk=value.pk)
        elif isinstance(value, QuerySet):
            should_return_model_instance = False
            queryset = value

        if queryset.model != cls._meta.model:
            raise Exception(f'{cls.__name__}.prepare() received a queryset from {queryset.model} model')

        if hasattr(cls, '_every_qs_preparation'):
            queryset = cls._every_qs_preparation(queryset, selection, info)

        sub_selection_by_field_name = {to_snake_case(s.name.value): s for s in selection.selection_set.selections}
        for field_name, functions in cls._preparation_functions_by_field.items():
            if field_name in sub_selection_by_field_name:
                sub_selection = sub_selection_by_field_name[field_name]
                for func in functions:
                    queryset = func(queryset, sub_selection, info)

        if should_return_model_instance:
            return queryset.first()
        else:
            return queryset

    @classmethod
    def append_field_preparation_function(cls, field_name, preparation_function):
        cls._preparation_functions_by_field[field_name] = cls._preparation_functions_by_field.get(field_name, [])
        cls._preparation_functions_by_field[field_name].append(preparation_function)

    @classmethod
    def register_model_field(cls, model, field_name):
        model_field = model._meta.get_field(field_name)
        related_model = model_field.related_model
        graphene_field = cls.convert_model_field_to_graphene_type(model_field)
        setattr(cls, field_name, graphene_field)
        if related_model:
            def prepare_function(queryset, selection, info):
                graphene_type = get_type_of_field(cls, field_name)
                related_qs = related_model.objects.all()
                related_qs = graphene_type.prepare(related_qs, selection, info)
                return queryset.prefetch_related(Prefetch(field_name, queryset=related_qs))
            cls.append_field_preparation_function(field_name, prepare_function)

    @classmethod
    def register_annotate_function(cls, field_name, annotate_function):
        info_in_params = cls.validate_function_signature(annotate_function, num_params_besides_info=1)
        def _annotate_function(queryset, _selection, info):
            args = [queryset]
            if info_in_params:
                args.append(info)

            return annotate_function( *args )

        cls.append_field_preparation_function(field_name, _annotate_function)

    @classmethod
    def prepare_prefetch_obj(cls, prefetch_obj, selection, info):
        related_model = get_related_model_from_lookup(cls._meta.model, prefetch_obj.prefetch_through)
        related_queryset = prefetch_obj.queryset
        if related_queryset is None:
            related_queryset = related_model.objects.all()
        related_type = get_global_registry().get_type_for_model(related_model)
        prefetch_obj.queryset = related_type.prepare(related_queryset, selection, info)

    @classmethod
    def register_every_qs_preparation(cls):
        if hasattr(cls, 'every_qs_preparation'):
            info_in_params = cls.validate_function_signature(cls.every_qs_preparation, num_params_besides_info=1)
            def _every_qs_preparation(queryset, _selection, info):
                args = [queryset]
                if info_in_params:
                    args.append(info)
                return cls.every_qs_preparation( *args )
            cls._every_qs_preparation = _every_qs_preparation

    @classmethod
    def register_meta_fields(cls, model, fields):
        if not fields:
            return

        model_fields_set = {field.name for field in model._meta.get_fields()}
        for field_name in fields:
            if field_name in model_fields_set:
                cls.register_model_field(model, field_name)
            else:
                raise Exception(f'{cls.__name__} field registration error ({field_name}): \
                                  specification must be a string of model field name.')

    @classmethod
    def register_attr_fields(cls):
        for field_name in dir(cls):
            field_specification = getattr(cls, field_name)
            if isinstance(field_specification, (UnmountedType, MountedType,)):
                annotate_function = getattr(cls, f'annotate_{field_name}', None)
                if annotate_function:
                    cls.register_annotate_function(field_name, annotate_function)

    # ---- </ Fernando Code > ----

class ErrorType(ObjectType):
    field = graphene.String(required=True)
    messages = graphene.List(graphene.NonNull(graphene.String), required=True)

    @classmethod
    def from_errors(cls, errors):
        data = camelize(errors) if graphene_settings.CAMELCASE_ERRORS else errors
        return [cls(field=key, messages=value) for key, value in data.items()]


# ---- < Fernando Code > ----

def strip_list_and_nonnull_off(graphene_type):
    while hasattr(graphene_type, 'of_type'):
        graphene_type = graphene_type.of_type
    return graphene_type


def get_type_of_field(graphene_type, field_name):
    field = graphene_type._meta.fields[field_name]
    if isinstance(field, Dynamic):
        field = field.type()
    graphene_type_of_field = field.type
    graphene_type_of_field = strip_list_and_nonnull_off(graphene_type_of_field)
    return graphene_type_of_field


def get_related_model_from_lookup(model_class, lookup):
    model_ptr = model_class
    for field_name in lookup.split('__'):
        model_ptr = model_ptr._meta.get_field(field_name).related_model
    return model_ptr

# ---- </ Fernando Code > ----
