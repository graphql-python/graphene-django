from functools import partial

from django.db.models.query import QuerySet

from graphene.types import Field, List
from graphene.relay import ConnectionField, PageInfo
from graphql_relay.connection.arrayconnection import connection_from_list_slice

from .utils import DJANGO_FILTER_INSTALLED, maybe_queryset


class DjangoListField(Field):

    def __init__(self, _type, *args, **kwargs):
        super(DjangoListField, self).__init__(List(_type), *args, **kwargs)

    @property
    def model(self):
        return self.type.of_type._meta.node._meta.model

    @staticmethod
    def list_resolver(resolver, root, args, context, info):
        return maybe_queryset(resolver(root, args, context, info))

    def get_resolver(self, parent_resolver):
        return partial(self.list_resolver, parent_resolver)


class DjangoConnectionField(ConnectionField):

    def __init__(self, *args, **kwargs):
        self.on = kwargs.pop('on', False)
        super(DjangoConnectionField, self).__init__(*args, **kwargs)

    @property
    def node_type(self):
        return self.type._meta.node

    @property
    def model(self):
        return self.node_type._meta.model

    def get_manager(self):
        if self.on:
            return getattr(self.model, self.on)
        else:
            return self.model._default_manager

    @staticmethod
    def connection_resolver(resolver, connection, default_manager, root, args, context, info):
        iterable = resolver(root, args, context, info)
        if iterable is None:
            iterable = default_manager
        iterable = maybe_queryset(iterable)
        if isinstance(iterable, QuerySet):
            if iterable is not default_manager:
                iterable = maybe_queryset(default_manager)
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

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager())


def get_connection_field(*args, **kwargs):
    if DJANGO_FILTER_INSTALLED:
        from .filter.fields import DjangoFilterConnectionField
        return DjangoFilterConnectionField(*args, **kwargs)
    return DjangoConnectionField(*args, **kwargs)
