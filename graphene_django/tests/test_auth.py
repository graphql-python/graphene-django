import datetime
import sys

import pytest
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
from ..auth.decorators import node_require_permission, mutation_require_permission, connection_require_permission
from ..auth.utils import is_related_to_user, is_authorized_to_mutate_object
from ..rest_framework.mutation import SerializerMutation

pytestmark = pytest.mark.django_db

if sys.version_info > (3, 0):
    from unittest.mock import Mock
else:
    from mock import Mock


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
        if check_perms not in self.perms:
            return False
        return True


class Context(object):

    def __init__(self, user):
        self.user = user


user_authenticated = MockUserContext(authenticated=True)
user_anonymous = MockUserContext(authenticated=False)
user_with_permissions = MockUserContext(authenticated=True, perms=('can_view_foo', 'can_view_bar'))


class MyFakeModel(models.Model):
    cool_name = models.CharField(max_length=50)


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeModel
        fields = '__all__'


class ArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = '__all__'


class MySerializer(serializers.Serializer):
    text = serializers.CharField()
    model = MyModelSerializer()

    def create(self, validated_data):
        return validated_data


def test_is_related_to_user():
    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )
    r2 = Reporter.objects.create(
        first_name='Michael',
        last_name='Doe',
        email='mdoe@example.com',
        a_choice=1
    )
    a = Article.objects.create(
        headline='Article Node 1',
        pub_date=datetime.date.today(),
        reporter=r,
        editor=r,
        lang='es'
    )
    result_1 = is_related_to_user(a, r, 'reporter')
    result_2 = is_related_to_user(a, r2, 'reporter')
    assert result_1 is True
    assert result_2 is False


def test_is_authorized_to_mutate_object():
    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )
    r2 = Reporter.objects.create(
        first_name='Michael',
        last_name='Doe',
        email='mdoe@example.com',
        a_choice=1
    )
    Article.objects.create(
        headline='Article Node 1',
        pub_date=datetime.date.today(),
        reporter=r,
        editor=r,
        lang='es'
    )
    result_1 = is_authorized_to_mutate_object(Article, r, 1, 'reporter')
    result_2 = is_authorized_to_mutate_object(Article, r2, 1, 'reporter')
    assert result_1 is True
    assert result_2 is False


def test_node_anonymous_user():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    Reporter.objects.create(
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


def test_node_no_context():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    Reporter.objects.create(
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
    result = schema.execute(query)
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

    Reporter.objects.create(
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

    Reporter.objects.create(
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


def test_auth_mutate_and_get_payload_anonymous():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

        @classmethod
        @mutation_require_permission(permissions=('can_view_foo', ))
        def mutate_and_get_payload(cls, root, info, **input):
            return super(MyMutation, cls).mutate_and_get_payload(root, info, **input)

    context = Context(user=user_anonymous)
    request = Mock(context=context, user=user_anonymous)
    result = MyMutation.mutate_and_get_payload(root=None, info=request, **{
        'text': 'value',
        'model': {
            'cool_name': 'other_value'
        }
    })
    assert result.errors is not None


def test_auth_mutate_and_get_payload_autheticated():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

        @classmethod
        @mutation_require_permission(permissions=('can_view_foo', ))
        def mutate_and_get_payload(cls, root, info, **input):
            return super(MyMutation, cls).mutate_and_get_payload(root, info, **input)

    context = Context(user=user_authenticated)
    request = Mock(context=context, user=user_authenticated)
    result = MyMutation.mutate_and_get_payload(root=None, info=request, **{
        'text': 'value',
        'model': {
            'cool_name': 'other_value'
        }
    })
    assert result.errors is not None


def test_auth_mutate_and_get_payload_with_permissions():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

        @classmethod
        @mutation_require_permission(permissions=('can_view_foo', ))
        def mutate_and_get_payload(cls, root, info, **input):
            return super(MyMutation, cls).mutate_and_get_payload(root, info, **input)

    context = Context(user=user_with_permissions)
    request = Mock(context=context, user=user_with_permissions)
    result = MyMutation.mutate_and_get_payload(root=None, info=request, **{
        'text': 'value',
        'model': {
            'cool_name': 'other_value'
        }
    })
    assert result.errors is None


def test_auth_connection():

    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

    class ArticleType(DjangoObjectType):

        class Meta:
            model = Article
            interfaces = (Node, )
            filter_fields = ('lang', 'headline')

    class MyAuthDjangoConnectionField(DjangoConnectionField):

        @classmethod
        @connection_require_permission(permissions=('can_view_foo', ))
        def connection_resolver(cls, resolver, connection, default_manager, max_limit,
                                enforce_first_or_last, root, info, **args):
            return super(MyAuthDjangoConnectionField, cls).connection_resolver(
                resolver, connection, default_manager, max_limit,
                enforce_first_or_last, root, info, **args)

    class Query(graphene.ObjectType):
        all_reporters = MyAuthDjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )
    Article.objects.create(
        headline='Article Node 1',
        pub_date=datetime.date.today(),
        reporter=r,
        editor=r,
        lang='es'
    )
    Article.objects.create(
        headline='Article Node 2',
        pub_date=datetime.date.today(),
        reporter=r,
        editor=r,
        lang='es'
    )
    Article.objects.create(
        headline='Article Node 3',
        pub_date=datetime.date.today(),
        reporter=r,
        editor=r,
        lang='en'
    )

    schema = graphene.Schema(query=Query)
    query = '''
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        id
                        articles(lang: "es", headline: "Article Node 1") {
                            edges {
                                node {
                                    id
                                }
                            }
                        }
                    }
                }
            }
        }
    '''

    expected = {
        'allReporters': {
            'edges': [{
                'node': {
                    'id': 'UmVwb3J0ZXJUeXBlOjE=',
                    'articles': {
                        'edges': [{
                            'node': {
                                'id': 'QXJ0aWNsZVR5cGU6MQ=='
                            }
                        }]
                    }
                }
            }]
        }
    }

    context = Context(user=user_with_permissions)
    request = Mock(context=context, user=user_with_permissions)
    result = schema.execute(query, context_value=request)
    assert not result.errors
    assert result.data == expected

    context = Context(user=user_anonymous)
    request = Mock(context=context, user=user_anonymous)
    result = schema.execute(query, context_value=request)
    assert result.errors
