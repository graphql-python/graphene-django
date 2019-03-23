#encoding=utf-8
from graphene.types.scalars import Boolean, Int

__author__ = "TimurMardanov"

know_parent = dict(know_parent=Boolean(default_value=True))
pagination = dict(first=Int(default_value=100), last=Int())


class GrapheneQLEdgeException(Exception):

    def __init__(self, message):
        self.message = message

    def __repr__(self, ):
        return self.message
