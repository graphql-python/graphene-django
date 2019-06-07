from functools import singledispatch
from typing import Union, Callable, Optional, Type
from types import GeneratorType
from functools import wraps, singledispatch

from django.utils.translation import ugettext as _
from graphene import String, List, ID, ObjectType, Field
from graphene.types.mountedtype import MountedType
from graphene.types.unmountedtype import UnmountedType
from graphene_django.types import DjangoObjectType
from neomodel import (
    StructuredNode,
    NodeSet,
)


from .lib import (
    GrapheneQLEdgeException,
    know_parent,
    pagination,
)


@singledispatch
def paginate_instance(qs, kwargs):
    """ Paginate difference of type qs.
    If list or tuple just primitive slicing
    If <NodeSet>
    """
    raise NotImplementedError("Type {} not implemented yet.".format(type(qs)))


def paginate(resolver):
    """ Paginator for resolver functions
    Input types:
        list, tuple, NodeSet
    """
    @wraps(resolver)
    def wrapper(root, info, **kwargs):
        qs = resolver(root, info, **kwargs)
        qs = paginate_instance(qs, kwargs)
        return qs
    return wrapper


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


@paginate_instance.register(list)
@paginate_instance.register(tuple)
@paginate_instance.register(GeneratorType)
def paginate_list(qs, kwargs):
    if 'first' in kwargs and 'last' in kwargs:
        qs = qs[:kwargs['first']]
        qs = qs[kwargs['last']:]
    elif 'first' in kwargs:
        qs = qs[:kwargs['first']]
    elif 'last' in kwargs:
        qs = qs[-kwargs['last']:]
    return qs



def EdgeNode(*args, **kwargs):
    """ Edge between nodes
    Attrs:
        cls_node -> ObjectType
            EdgeNode

        target_model: StructuredNode
            Target model in edge relationship
        target_field: str
            Field name of <StructuredNode> target model

        resolver -> function (None)
            override function if you need them

        description: str

        return_type:
            which graphene field is set

        kwargs : -> extra arguments
    """
    return EdgeNodeClass(*args, **kwargs).build()


class EdgeNodeClass:
    parent_type_exception = GrapheneQLEdgeException(_(
        'Parent type is incorrect for this field. Say to back'))

    def __init__(self, cls_node,
                 target_model = None,
                 target_field = None,
                 resolver = None,
                 description = "Edge Node",
                 return_type = List,
                 *args,
                 **kwargs):
        """
        Args:
            cls_node: Type[DjangoObjectType],
            target_model: Optional[Type[StructuredNode]] = None,
            target_field: Optional[str] = None,
            resolver: Optional[Callable] = None,
            description: str = "Edge Node",
            return_type: Union[MountedType, UnmountedType] = List,
            *args, **kwargs
        """
        self.cls_node = cls_node
        self._resolver = resolver
        self.description = description
        self._target_model = target_model
        self._target_field = target_field
        self.arg_fields = {
            'id': ID(required=False),
            **kwargs,
            **know_parent,
            **pagination
        }
        self.return_type = return_type

    def build(self, ):
        """ Build edgeNode manager
        """
        return self.return_type(self.cls_node,
                                **self.arg_fields,
                                description=self.description,
                                resolver=self.resolver)

    @property
    def resolver(self) -> Callable:
        """ Resolver function
        """
        return self.get_default_resolver() if self._resolver is None else self._resolver

    @property
    def target_model(self, ):
        if self._target_model is not None:
            return self._target_model
        raise GrapheneQLEdgeException(message="""
                target_model or resolver in EdgeNode
                should be defined""")

    @property
    def target_field(self, ):
        if self._target_field is None:
            return str(self.target_model.__class__).lower()
        return self._target_field

    def get_default_resolver(self, ):
        return get_resolver(self.return_type(String), self)  # just init list field


@singledispatch
def get_resolver(node_type, edge_node):
    raise NotImplementedError(f"{node_type} type isn't implemented yet")


@get_resolver.register(List)
def list_resolver(node_type, edge_node) -> Callable:
    @paginate
    def default_resolver(root, info, **kwargs) -> List:
        """ Default <List> resolver
        """
        rel_data = []
        relation_field = getattr(root, edge_node.target_field)

        # know_parent == None or False, return all relationships
        if not kwargs.get('know_parent'):
            return relation_field.all_relationships()
        else:
            if not hasattr(root, '_parent'):
                raise EdgeNodeClass.parent_type_exception
            else:
                rel_data = relation_field.all_relationships(root._parent)
        if kwargs.get('id'):
            rel_data = relation_field.all_relationships(
                edge_node.target_model.nodes.get(uid=kwargs['id']))
        return rel_data

    return default_resolver


@get_resolver.register(Field)
def field_resolver(node_type, edge_node) -> Callable:
    def default_resolver(root, info, **kwargs) -> Field:
        """ Default <Field> resolver
        """
        data = None
        relation_field = getattr(root, edge_node.target_field)

        if not kwargs.get('know_parent'):
            rels = relation_field.all_relationships()
            if rels:
                return rels[0]
            return None
        else:
            if not hasattr(root, '_parent'):
                raise EdgeNodeClass.parent_type_exception
            else:
                data = relation_field.relationship(root._parent)
        if kwargs.get('id'):
            data = relation_field.relationship(
                edge_node.target_model.nodes.get(uid=kwargs['id']))
        return data
    return default_resolver
