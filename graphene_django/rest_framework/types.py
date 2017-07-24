import graphene
from graphene.types.unmountedtype import UnmountedType


class ErrorType(graphene.ObjectType):
    field = graphene.String()
    messages = graphene.List(graphene.String)


class DictType(UnmountedType):
    key = graphene.String()
    value = graphene.String()
