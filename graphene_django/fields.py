from functools import partial

from django.db.models.query import QuerySet
from graphene import NonNull

from promise import Promise

from graphene.types import Field, List
from graphene.relay import ConnectionField, PageInfo
from graphql_relay.connection.arrayconnection import connection_from_list_slice

from .settings import graphene_settings
from .utils import maybe_queryset


class DjangoListField(Field):
    def __init__(self, _type, *args, **kwargs):
        # Django would never return a Set of None  vvvvvvv
        super(DjangoListField, self).__init__(List(NonNull(_type)), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @staticmethod
    def list_resolver(resolver, root, info, **args):
        return maybe_queryset(resolver(root, info, **args))

    def get_resolver(self, parent_resolver):
        return partial(self.list_resolver, parent_resolver)


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
        return connection._meta.node.get_queryset(queryset, info)

    @classmethod
    def merge_querysets(cls, default_queryset, queryset):
        if default_queryset.query.distinct and not queryset.query.distinct:
            queryset = queryset.distinct()
        elif queryset.query.distinct and not default_queryset.query.distinct:
            default_queryset = default_queryset.distinct()
        return queryset & default_queryset

    @classmethod
    def resolve_connection(cls, connection, default_manager, args, iterable):
        if iterable is None:
            iterable = default_manager
        iterable = maybe_queryset(iterable)
        if isinstance(iterable, QuerySet):
            if iterable.model.objects is not default_manager:
                default_queryset = maybe_queryset(default_manager)
                iterable = cls.merge_querysets(default_queryset, iterable)
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

        iterable = resolver(root, info, **args)
        queryset = cls.resolve_queryset(connection, default_manager, info, args)
        on_resolve = partial(cls.resolve_connection, connection, queryset, args)

        if Promise.is_thenable(iterable):
            return Promise.resolve(iterable).then(on_resolve)

        return on_resolve(iterable)

    def get_resolver(self, parent_resolver):
        return partial(
            self.connection_resolver,
            parent_resolver,
            self.connection_type,
            self.get_manager(),
            self.max_limit,
            self.enforce_first_or_last,
        )
