from functools import singledispatch
from typing import Union, Callable, Optional, Type

from django.utils.translation import ugettext as _
from graphene import String, List, ID, ObjectType, Field
from graphene.types.mountedtype import MountedType
from graphene.types.unmountedtype import UnmountedType
from graphene_django.types import DjangoObjectType
from neomodel.core import StructuredNode

from graphene_ql.decorators import paginate

from .lib import (
    GrapheneQLEdgeException,
    know_parent,
    pagination,
)


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

        if not kwargs.get('know_parent'):
            for rel_node in relation_field.filter():
                rel_data.append(relation_field.relationship(rel_node))
        else:
            if not hasattr(root, '_parent'):
                raise EdgeNodeClass.parent_type_exception
            else:
                rel_data = relation_field.filter_relationships(root._parent)
        if kwargs.get('id'):
            rel_data = relation_field.filter_relationships(
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
            data = relation_field.filter().first_or_none()
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
