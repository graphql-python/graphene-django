import datetime

import pytest
from unittest.mock import Mock
from django.db import models
from django.utils.functional import SimpleLazyObject
from py.test import raises

import graphene
from graphene.relay import Node
from rest_framework import serializers

from ..utils import DJANGO_FILTER_INSTALLED
from ..compat import MissingType, JSONField
from ..fields import DjangoConnectionField
from ..types import DjangoObjectType
from ..settings import graphene_settings
from .models import Article, Reporter
from ..auth.decorators import node_require_permission, mutation_require_permission
from ..rest_framework.mutation import SerializerMutation

pytestmark = pytest.mark.django_db


class MockUserContext(object):

    def __init__(self, username='carlosmart', authenticated=True, is_staff=False, superuser=False, perms=()):
        self.user = self
        self.username = username
        self.authenticated = authenticated
        self.is_staff = is_staff
        self.is_superuser = superuser
        self.perms = perms

    def is_authenticated(self):
        return self.authenticated

    def has_perm(self, check_perms):
        print(self.username, self.perms)
        if check_perms not in self.perms:
            print("NO PERMS")
            return False
        print("HAS PERMS")
        return True


class Context(object):

    def __init__(self, user):
        self.user = user


user_authenticated = MockUserContext(authenticated=True)
user_anonymous = MockUserContext(authenticated=False)
user_with_permissions = MockUserContext(authenticated=True, perms=('can_view_foo', 'can_view_bar'))


# Mutations
class MyFakeModel(models.Model):
    cool_name = models.CharField(max_length=50)


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeModel
        fields = '__all__'


class MySerializer(serializers.Serializer):
    text = serializers.CharField()
    model = MyModelSerializer()

    def create(self, validated_data):
        return validated_data


def test_node_anonymous_user():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )

    class Query(graphene.ObjectType):
        reporter = Node.Field(ReporterType)

    schema = graphene.Schema(query=Query)
    query = '''
        query {
          reporter(id: "UmVwb3J0ZXJUeXBlOjE="){
            firstName
          }
        }
    '''
    context = Context(user=user_anonymous)
    request = Mock(context=context, user=user_anonymous)
    result = schema.execute(query, context_value=request)
    assert result.errors
    assert result.data == {
        'reporter': None
    }


def test_node_authenticated_user_no_permissions():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )

    class Query(graphene.ObjectType):
        reporter = Node.Field(ReporterType)

    schema = graphene.Schema(query=Query)
    query = '''
        query {
          reporter(id: "UmVwb3J0ZXJUeXBlOjE="){
            firstName
          }
        }
    '''
    context = Context(user=user_authenticated)
    request = Mock(context=context, user=user_authenticated)
    result = schema.execute(query, context_value=request)
    assert result.errors
    assert result.data == {
        'reporter': None
    }


def test_node_authenticated_user_with_permissions():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )

    class Query(graphene.ObjectType):
        reporter = Node.Field(ReporterType)

    schema = graphene.Schema(query=Query)
    query = '''
        query {
          reporter(id: "UmVwb3J0ZXJUeXBlOjE="){
            firstName
          }
        }
    '''
    context = Context(user=user_with_permissions)
    request = Mock(context=context, user=user_with_permissions)
    result = schema.execute(query, context_value=request)
    assert not result.errors
    assert result.data == {
        'reporter': {
            'firstName': 'John'
        }
    }


def test_mutate_and_get_payload_success():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

        @mutation_require_permission(permissions=('can_view_foo', ))
        def mutate_and_get_payload(cls, root, info, **input):
            return super(MyMutation, cls).mutate_and_get_payload(root, info, **input)

    context = Context(user=user_with_permissions)
    request = Mock(context=context, user=user_with_permissions)
    result = MyMutation.mutate_and_get_payload(None, request, **{
        'text': 'value',
        'model': {
            'cool_name': 'other_value'
        }
    })
    assert result.errors is None
