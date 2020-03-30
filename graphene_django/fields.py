from functools import partial

import six
from django.db.models.query import QuerySet
from graphql_relay.connection.arrayconnection import connection_from_list_slice
from promise import Promise

from graphene import NonNull
from graphene.relay import ConnectionField, PageInfo
from graphene.types import Field, List

from .settings import graphene_settings
from .utils import maybe_queryset


class DjangoListField(Field):
    def __init__(self, _type, *args, **kwargs):
        from .types import DjangoObjectType

        if isinstance(_type, NonNull):
            _type = _type.of_type

        # Django would never return a Set of None  vvvvvvv
        super(DjangoListField, self).__init__(List(NonNull(_type)), *args, **kwargs)

        assert issubclass(
            self._underlying_type, DjangoObjectType
        ), "DjangoListField only accepts DjangoObjectType types"

    @property
    def _underlying_type(self):
        _type = self._type
        while hasattr(_type, "of_type"):
            _type = _type.of_type
        return _type

    @property
    def model(self):
        return self._underlying_type._meta.model

    @staticmethod
    def list_resolver(django_object_type, resolver, root, info, **args):
        queryset = maybe_queryset(resolver(root, info, **args))
        if queryset is None:
            # Default to Django Model queryset
            # N.B. This happens if DjangoListField is used in the top level Query object
            model_manager = django_object_type._meta.model.objects
            queryset = maybe_queryset(
                django_object_type.get_queryset(model_manager, info)
            )
        return queryset

    def get_resolver(self, parent_resolver):
        _type = self.type
        if isinstance(_type, NonNull):
            _type = _type.of_type
        django_object_type = _type.of_type.of_type
        return partial(self.list_resolver, django_object_type, parent_resolver)


class DjangoConnectionField(ConnectionField):
    def __init__(self, *args, **kwargs):
        self.on = kwargs.pop("on", False)
        self.max_limit = kwargs.pop(
            "max_limit", graphene_settings.RELAY_CONNECTION_MAX_LIMIT
        )
        self.enforce_first_or_last = kwargs.pop(
            "enforce_first_or_last",
            graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST,
        )
        super(DjangoConnectionField, self).__init__(*args, **kwargs)

    @property
    def type(self):
        from .types import DjangoObjectType

        _type = super(ConnectionField, self).type
        non_null = False
        if isinstance(_type, NonNull):
            _type = _type.of_type
            non_null = True
        assert issubclass(
            _type, DjangoObjectType
        ), "DjangoConnectionField only accepts DjangoObjectType types"
        assert _type._meta.connection, "The type {} doesn't have a connection".format(
            _type.__name__
        )
        connection_type = _type._meta.connection
        if non_null:
            return NonNull(connection_type)
        return connection_type

    @property
    def connection_type(self):
        type = self.type
        if isinstance(type, NonNull):
            return type.of_type
        return type

    @property
    def node_type(self):
        return self.connection_type._meta.node

    @property
    def model(self):
        return self.node_type._meta.model

    def get_manager(self):
        if self.on:
            return getattr(self.model, self.on)
        else:
            return self.model._default_manager

    @classmethod
    def resolve_queryset(cls, connection, queryset, info, args):
        # queryset is the resolved iterable from ObjectType
        return connection._meta.node.get_queryset(queryset, info)

    @classmethod
    def resolve_connection(cls, connection, args, iterable):
        iterable = maybe_queryset(iterable)
        if isinstance(iterable, QuerySet):
            _len = iterable.count()
        else:
            _len = len(iterable)
        connection = connection_from_list_slice(
            iterable,
            args,
            slice_start=0,
            list_length=_len,
            list_slice_length=_len,
            connection_type=connection,
            edge_type=connection.Edge,
            pageinfo_type=PageInfo,
        )
        connection.iterable = iterable
        connection.length = _len
        return connection

    @classmethod
    def connection_resolver(
        cls,
        resolver,
        connection,
        default_manager,
        queryset_resolver,
        max_limit,
        enforce_first_or_last,
        root,
        info,
        **args
    ):
        first = args.get("first")
        last = args.get("last")

        if enforce_first_or_last:
            assert first or last, (
                "You must provide a `first` or `last` value to properly paginate the `{}` connection."
            ).format(info.field_name)

        if max_limit:
            if first:
                assert first <= max_limit, (
                    "Requesting {} records on the `{}` connection exceeds the `first` limit of {} records."
                ).format(first, info.field_name, max_limit)
                args["first"] = min(first, max_limit)

            if last:
                assert last <= max_limit, (
                    "Requesting {} records on the `{}` connection exceeds the `last` limit of {} records."
                ).format(last, info.field_name, max_limit)
                args["last"] = min(last, max_limit)

        # eventually leads to DjangoObjectType's get_queryset (accepts queryset)
        # or a resolve_foo (does not accept queryset)
        iterable = resolver(root, info, **args)
        if iterable is None:
            iterable = default_manager
        # thus the iterable gets refiltered by resolve_queryset
        # but iterable might be promise
        iterable = queryset_resolver(connection, iterable, info, args)
        on_resolve = partial(cls.resolve_connection, connection, args)

        if Promise.is_thenable(iterable):
            return Promise.resolve(iterable).then(on_resolve)

        return on_resolve(iterable)

    def get_resolver(self, parent_resolver):
        return partial(
            self.connection_resolver,
            parent_resolver,
            self.connection_type,
            self.get_manager(),
            self.get_queryset_resolver(),
            self.max_limit,
            self.enforce_first_or_last,
        )

    def get_queryset_resolver(self):
        return self.resolve_queryset
