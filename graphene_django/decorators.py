from inspect import isclass
from types import GeneratorType
from typing import Callable
from functools import wraps, partial, singledispatch
from graphene.relay.node import from_global_id
from graphene.types.objecttype import ObjectType


@singledispatch
def paginate_instance(qs, kwargs):
    """ Paginate difference of type qs.
    If list or tuple just primitive slicing
    If <NodeSet>
    """
    raise NotImplementedError("Type {} not implemented yet.".format(type(qs)))


def paginate(resolver):
    """ Paginator for resolver functions
    Input types (iterable):
        list, tuple, NodeSet
    """
    @wraps(resolver)
    def wrapper(root, info, **kwargs):
        qs = resolver(root, info, **kwargs)
        qs = paginate_instance(qs, kwargs)
        return qs
    return wrapper


@paginate_instance.register(list)
@paginate_instance.register(tuple)
@paginate_instance.register(GeneratorType)
def paginate_list(qs, kwargs):
    """ Base pagination dispatcher by iterable pythonic collections
    """
    if 'first' in kwargs and 'last' in kwargs:
        qs = qs[:kwargs['first']]
        qs = qs[kwargs['last']:]
    elif 'first' in kwargs:
        qs = qs[:kwargs['first']]
    elif 'last' in kwargs:
        qs = qs[-kwargs['last']:]
    return qs


try:
    from neomodel.match import NodeSet # noqa

    @paginate_instance.register(NodeSet)
    def paginate_nodeset(qs, kwargs):
        # Warning. Type of pagination is lazy
        if 'first' in kwargs and 'last' in kwargs:
            qs = qs.set_skip(kwargs['first'] - kwargs['last'])
            qs = qs.set_limit(kwargs['last'])
        elif 'last' in kwargs:
            count = len(qs)
            qs = qs.set_skip(count - kwargs['last'])
            qs = qs.set_limit(kwargs['last'])
        elif 'first' in kwargs:
            qs = qs.set_limit(kwargs['first'])
        return qs
except:
    raise NotImplementedError("Neomodel does not installed")
finally:
    print('Install custom neomodel (ver=3.0.0)')


def check_connection(func):
    """ Check that node is ObjectType
    """
    @wraps(func)
    def wrapper(node_, resolver, *args, **kwargs):
        if not (isclass(node_) and issubclass(node_, ObjectType)):
            raise NotImplementedError("{} not implemented.".format(type(node_)))
        kwargs['registry_name'] = node_.__name__
        return func(node_, resolver, *args, **kwargs)
    return wrapper
