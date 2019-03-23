from types import FunctionType, GeneratorType
from functools import reduce, partial
from graphene import (
    NonNull, Boolean,
    relay,
    Int,
    Connection as GConnection,
    ObjectType,
    Field,
    List,
    Enum,
    JSONString as JString,
)
from graphene_django.fields import DjangoConnectionField as DjangoConnectionFieldOriginal
from graphene_django.forms.converter import convert_form_field
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_django.filter.utils import (
    get_filtering_args_from_filterset,
    get_filterset_class
)
from lazy_import import lazy_callable, LazyCallable, lazy_module

from ..decorators import check_connection, paginate_instance
from ..utils import pagination_params

try:
    from neomodel.match import NodeSet # noqa
except:
    raise ImportError("Install neomodel.")


class ConnectionField(relay.ConnectionField):
    """ Push node connection kwargs into ConnectionEdge.hidden_kwargs
    """
    @classmethod
    def resolve_connection(cls, connection_type, args, resolved):
        connection = super(ConnectionField, cls).resolve_connection(connection_type, args, resolved)
        connection.hidden_kwargs = args
        return connection


@check_connection
def Connection(node_, resolver, *args, **kwargs):
    """
    node_: [ObjectType, DjangoObjectType],
               resolver,
               *args,
               **kwargs

    Connection class which working with custom
    ObjectTypes and Nodes and supports base connection.

    node, resolver - required named arguments
    args, kwargs - base Field arguments

    Can custom count
    """
    kwargs = {**pagination_params, **kwargs}
    registry_name = kwargs.pop('registry_name')
    override_name = kwargs.pop('name', '')

    meta_name = "{}{}CustomEdgeConnection".format(registry_name,
                                                  override_name)

    class EdgeConnection(ObjectType):
        node = Field(node_)

        class Meta:
            name = meta_name

        def __init__(self, node, *args, **kwargs):
            if callable(node):
                raise TypeError("node_resolver is not callable object")
            super(EdgeConnection, self).__init__(*args, **kwargs)
            self._node = node

        def resolve_node(self, info, **kwargs):
            return self._node

    meta_name_connection = "{}{}CustomConnection".format(registry_name,
                                                         override_name)

    class ConnectionDecorator(ObjectType):
        edges = List(EdgeConnection)
        total_count = Int()

        class Meta:
            name = meta_name_connection

        def __init__(self, *args, **kwargs):
            self.resolver_ = kwargs.pop('pr', None)
            super(ConnectionDecorator, self).__init__(*args, **kwargs)

        def resolve_edges(self, info, **kwargs):
            items = self.resolver_(**kwargs)
            return [EdgeConnection(node=item, **kwargs) for item in items]

        def resolve_total_count(self, info, **kwargs):
            """ Custom total count resolver
            """
            result = self.resolver_(count=True)
            if isinstance(result, GeneratorType):
                result = list(result)
            elif isinstance(result, int):
                return result
            elif isinstance(result, NodeSet):
                return len(result.set_skip(0).set_limit(1))
            if isinstance(result, (list, tuple)) and result:
                if isinstance(result[0], int):
                    # if returned count manually
                    return result[0]
                # if returned iterable object
                return len(result)

    def resolve_connection_decorator(root, info, **kwargs):
        resolver_ = partial(resolver, root, info, *args, **kwargs)
        return ConnectionDecorator(pr=resolver_)

    return Field(ConnectionDecorator, resolver=resolve_connection_decorator, *args, **kwargs)


def RelayConnection(node_, *args, **kwargs):
    """ node_: [ObjectType, DjangoObjectType, Callable],
                    *args,
                    **kwargs
    Quick implementation of stock relay connection
    # node: should contains relay.Node in Meta.interfaces

    + total_count implements
    def - total_count_resolver: custom function for resolve total_count
    """
    registry_name = kwargs.pop('name', '')
    total_count_resolver = kwargs.pop('total_count_resolver', None)

    def Connection(node_):
        node_ = node_() if isinstance(node_, FunctionType) else node_

        if isinstance(node_, LazyCallable):
            node_()

        meta_name = "{}{}CC".format(node_.__name__, registry_name)

        class CustomConnection(relay.Connection):
            class Meta:
                node = node_
                name = meta_name

            def __init__(self, *ar, **kw):
                super(CustomConnection, self).__init__(*ar, **kw)
                self._extra_kwargs = kwargs

            total_count = Int()

            def resolve_total_count(self, info, **params):
                if total_count_resolver:
                    return total_count_resolver(self, info, **self.hidden_kwargs)
                if isinstance(self.iterable, NodeSet):
                    return len(self.iterable.set_skip(0).set_limit(1))
                elif isinstance(self.iterable, (list, tuple)):
                    return len(list(self.iterable))
                return 0
        return CustomConnection

    return ConnectionField(lambda: Connection(node_), *args, **kwargs)
