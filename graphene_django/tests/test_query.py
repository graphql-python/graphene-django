import datetime

import pytest
from django.db import models
from django.utils.functional import SimpleLazyObject
from py.test import raises

import graphene
from graphene.relay import Node

from ..utils import DJANGO_FILTER_INSTALLED
from ..compat import MissingType, JSONField
from ..fields import DjangoConnectionField
from ..types import DjangoObjectType
from ..settings import graphene_settings
from .models import Article, Reporter

pytestmark = pytest.mark.django_db


def test_should_query_only_fields():
    with raises(Exception):
        class ReporterType(DjangoObjectType):

            class Meta:
                model = Reporter
                only_fields = ('articles', )

        schema = graphene.Schema(query=ReporterType)
        query = '''
            query ReporterQuery {
              articles
            }
        '''
        result = schema.execute(query)
        assert not result.errors


def test_should_query_simplelazy_objects():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            only_fields = ('id', )

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, args, context, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = '''
        query {
          reporter {
            id
          }
        }
    '''
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {
        'reporter': {
            'id': '1'
        }
    }


def test_should_query_well():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, *args, **kwargs):
            return Reporter(first_name='ABA', last_name='X')

    query = '''
        query ReporterQuery {
          reporter {
            firstName,
            lastName,
            email
          }
        }
    '''
    expected = {
        'reporter': {
            'firstName': 'ABA',
            'lastName': 'X',
            'email': ''
        }
    }
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(JSONField is MissingType,
                    reason="RangeField should exist")
def test_should_query_postgres_fields():
    from django.contrib.postgres.fields import IntegerRangeField, ArrayField, JSONField, HStoreField

    class Event(models.Model):
        ages = IntegerRangeField(help_text='The age ranges')
        data = JSONField(help_text='Data')
        store = HStoreField()
        tags = ArrayField(models.CharField(max_length=50))

    class EventType(DjangoObjectType):

        class Meta:
            model = Event

    class Query(graphene.ObjectType):
        event = graphene.Field(EventType)

        def resolve_event(self, *args, **kwargs):
            return Event(
                ages=(0, 10),
                data={'angry_babies': True},
                store={'h': 'store'},
                tags=['child', 'angry', 'babies']
            )

    schema = graphene.Schema(query=Query)
    query = '''
        query myQuery {
          event {
            ages
            tags
            data
            store
          }
        }
    '''
    expected = {
        'event': {
            'ages': [0, 10],
            'tags': ['child', 'angry', 'babies'],
            'data': '{"angry_babies": true}',
            'store': '{"h": "store"}',
        },
    }
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_node():
    # reset_global_registry()
    # Node._meta.registry = get_global_registry()

    class ReporterNode(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        def get_node(cls, id, context, info):
            return Reporter(id=2, first_name='Cookie Monster')

        def resolve_articles(self, *args, **kwargs):
            return [Article(headline='Hi!')]

    class ArticleNode(DjangoObjectType):

        class Meta:
            model = Article
            interfaces = (Node, )

        @classmethod
        def get_node(cls, id, context, info):
            return Article(id=1, headline='Article node', pub_date=datetime.date(2002, 3, 11))

    class Query(graphene.ObjectType):
        node = Node.Field()
        reporter = graphene.Field(ReporterNode)
        article = graphene.Field(ArticleNode)

        def resolve_reporter(self, *args, **kwargs):
            return Reporter(id=1, first_name='ABA', last_name='X')

    query = '''
        query ReporterQuery {
          reporter {
            id,
            firstName,
            articles {
              edges {
                node {
                  headline
                }
              }
            }
            lastName,
            email
          }
          myArticle: node(id:"QXJ0aWNsZU5vZGU6MQ==") {
            id
            ... on ReporterNode {
                firstName
            }
            ... on ArticleNode {
                headline
                pubDate
            }
          }
        }
    '''
    expected = {
        'reporter': {
            'id': 'UmVwb3J0ZXJOb2RlOjE=',
            'firstName': 'ABA',
            'lastName': 'X',
            'email': '',
            'articles': {
                'edges': [{
                  'node': {
                      'headline': 'Hi!'
                  }
                }]
            },
        },
        'myArticle': {
            'id': 'QXJ0aWNsZU5vZGU6MQ==',
            'headline': 'Article node',
            'pubDate': '2002-03-11',
        }
    }
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_connectionfields():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )
            only_fields = ('articles', )

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

        def resolve_all_reporters(self, args, context, info):
            return [Reporter(id=1)]

    schema = graphene.Schema(query=Query)
    query = '''
        query ReporterConnectionQuery {
          allReporters {
            pageInfo {
              hasNextPage
            }
            edges {
              node {
                id
              }
            }
          }
        }
    '''
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {
        'allReporters': {
            'pageInfo': {
                'hasNextPage': False,
            },
            'edges': [{
                'node': {
                    'id': 'UmVwb3J0ZXJUeXBlOjE='
                }
            }]
        }
    }


@pytest.mark.skipif(not DJANGO_FILTER_INSTALLED,
                    reason="django-filter should be installed")
def test_should_query_node_filtering():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

    class ArticleType(DjangoObjectType):

        class Meta:
            model = Article
            interfaces = (Node, )
            filter_fields = ('lang', )

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

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
        lang='en'
    )

    schema = graphene.Schema(query=Query)
    query = '''
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        id
                        articles(lang: "es") {
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

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(not DJANGO_FILTER_INSTALLED,
                    reason="django-filter should be installed")
def test_should_query_node_multiple_filtering():
    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

    class ArticleType(DjangoObjectType):

        class Meta:
            model = Article
            interfaces = (Node, )
            filter_fields = ('lang', 'headline')

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

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

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_enforce_first_or_last():
    graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST = True

    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )

    schema = graphene.Schema(query=Query)
    query = '''
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    '''

    expected = {
        'allReporters': None
    }

    result = schema.execute(query)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        'You must provide a `first` or `last` value to properly '
        'paginate the `allReporters` connection.'
    )
    assert result.data == expected


def test_should_error_if_first_is_greater_than_max():
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 100

    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name='John',
        last_name='Doe',
        email='johndoe@example.com',
        a_choice=1
    )

    schema = graphene.Schema(query=Query)
    query = '''
        query NodeFilteringQuery {
            allReporters(first: 101) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    '''

    expected = {
        'allReporters': None
    }

    result = schema.execute(query)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        'Requesting 101 records on the `allReporters` connection '
        'exceeds the `first` limit of 100 records.'
    )
    assert result.data == expected

    graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST = False
