import datetime
import base64

import pytest
from django.db import models
from django.db.models import Q
from django.utils.functional import SimpleLazyObject
from graphql_relay import to_global_id
from py.test import raises

import graphene
from graphene.relay import Node

from ..compat import JSONField, MissingType
from ..fields import DjangoConnectionField
from ..types import DjangoObjectType
from ..utils import DJANGO_FILTER_INSTALLED
from .models import Article, CNNReporter, Film, FilmDetails, Reporter


def test_should_query_only_fields():
    with raises(Exception):

        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter
                fields = ("articles",)

        schema = graphene.Schema(query=ReporterType)
        query = """
            query ReporterQuery {
              articles
            }
        """
        result = schema.execute(query)
        assert not result.errors


def test_should_query_simplelazy_objects():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = ("id",)

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: Reporter(id=1))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_should_query_wrapped_simplelazy_objects():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = ("id",)

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, info):
            return SimpleLazyObject(lambda: SimpleLazyObject(lambda: Reporter(id=1)))

    schema = graphene.Schema(query=Query)
    query = """
        query {
          reporter {
            id
          }
        }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {"reporter": {"id": "1"}}


def test_should_query_well():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter

    class Query(graphene.ObjectType):
        reporter = graphene.Field(ReporterType)

        def resolve_reporter(self, info):
            return Reporter(first_name="ABA", last_name="X")

    query = """
        query ReporterQuery {
          reporter {
            firstName,
            lastName,
            email
          }
        }
    """
    expected = {"reporter": {"firstName": "ABA", "lastName": "X", "email": ""}}
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(JSONField is MissingType, reason="RangeField should exist")
def test_should_query_postgres_fields():
    from django.contrib.postgres.fields import (
        IntegerRangeField,
        ArrayField,
        JSONField,
        HStoreField,
    )

    class Event(models.Model):
        ages = IntegerRangeField(help_text="The age ranges")
        data = JSONField(help_text="Data")
        store = HStoreField()
        tags = ArrayField(models.CharField(max_length=50))

    class EventType(DjangoObjectType):
        class Meta:
            model = Event

    class Query(graphene.ObjectType):
        event = graphene.Field(EventType)

        def resolve_event(self, info):
            return Event(
                ages=(0, 10),
                data={"angry_babies": True},
                store={"h": "store"},
                tags=["child", "angry", "babies"],
            )

    schema = graphene.Schema(query=Query)
    query = """
        query myQuery {
          event {
            ages
            tags
            data
            store
          }
        }
    """
    expected = {
        "event": {
            "ages": [0, 10],
            "tags": ["child", "angry", "babies"],
            "data": '{"angry_babies": true}',
            "store": '{"h": "store"}',
        }
    }
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_node():
    class ReporterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

        @classmethod
        def get_node(cls, info, id):
            return Reporter(id=2, first_name="Cookie Monster")

        def resolve_articles(self, info, **args):
            return [Article(headline="Hi!")]

    class ArticleNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)

        @classmethod
        def get_node(cls, info, id):
            return Article(
                id=1, headline="Article node", pub_date=datetime.date(2002, 3, 11)
            )

    class Query(graphene.ObjectType):
        node = Node.Field()
        reporter = graphene.Field(ReporterNode)
        article = graphene.Field(ArticleNode)

        def resolve_reporter(self, info):
            return Reporter(id=1, first_name="ABA", last_name="X")

    query = """
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
    """
    expected = {
        "reporter": {
            "id": "UmVwb3J0ZXJOb2RlOjE=",
            "firstName": "ABA",
            "lastName": "X",
            "email": "",
            "articles": {"edges": [{"node": {"headline": "Hi!"}}]},
        },
        "myArticle": {
            "id": "QXJ0aWNsZU5vZGU6MQ==",
            "headline": "Article node",
            "pubDate": "2002-03-11",
        },
    }
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_onetoone_fields():
    film = Film(id=1)
    film_details = FilmDetails(id=1, film=film)

    class FilmNode(DjangoObjectType):
        class Meta:
            model = Film
            interfaces = (Node,)

    class FilmDetailsNode(DjangoObjectType):
        class Meta:
            model = FilmDetails
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        film = graphene.Field(FilmNode)
        film_details = graphene.Field(FilmDetailsNode)

        def resolve_film(root, info):
            return film

        def resolve_film_details(root, info):
            return film_details

    query = """
        query FilmQuery {
          filmDetails {
            id
            film {
              id
            }
          }
          film {
            id
            details {
              id
            }
          }
        }
    """
    expected = {
        "filmDetails": {
            "id": "RmlsbURldGFpbHNOb2RlOjE=",
            "film": {"id": "RmlsbU5vZGU6MQ=="},
        },
        "film": {
            "id": "RmlsbU5vZGU6MQ==",
            "details": {"id": "RmlsbURldGFpbHNOb2RlOjE="},
        },
    }
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_connectionfields():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = ("articles",)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return [Reporter(id=1)]

    schema = graphene.Schema(query=Query)
    query = """
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
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data == {
        "allReporters": {
            "pageInfo": {"hasNextPage": False},
            "edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjE="}}],
        }
    }


def test_should_keep_annotations():
    from django.db.models import Count, Avg

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = ("articles",)

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ("lang",)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)
        all_articles = DjangoConnectionField(ArticleType)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.annotate(articles_c=Count("articles")).order_by(
                "articles_c"
            )

        def resolve_all_articles(self, info, **args):
            return Article.objects.annotate(import_avg=Avg("importance")).order_by(
                "import_avg"
            )

    schema = graphene.Schema(query=Query)
    query = """
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
          allArticles {
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
    """
    result = schema.execute(query)
    assert not result.errors


@pytest.mark.skipif(
    not DJANGO_FILTER_INSTALLED, reason="django-filter should be installed"
)
def test_should_query_node_filtering():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ("lang",)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )
    Article.objects.create(
        headline="Article Node 1",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 2",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="en",
    )

    schema = graphene.Schema(query=Query)
    query = """
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
    """

    expected = {
        "allReporters": {
            "edges": [
                {
                    "node": {
                        "id": "UmVwb3J0ZXJUeXBlOjE=",
                        "articles": {
                            "edges": [{"node": {"id": "QXJ0aWNsZVR5cGU6MQ=="}}]
                        },
                    }
                }
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(
    not DJANGO_FILTER_INSTALLED, reason="django-filter should be installed"
)
def test_should_query_node_filtering_with_distinct_queryset():
    class FilmType(DjangoObjectType):
        class Meta:
            model = Film
            interfaces = (Node,)
            filter_fields = ("genre",)

    class Query(graphene.ObjectType):
        films = DjangoConnectionField(FilmType)

        # def resolve_all_reporters_with_berlin_films(self, args, context, info):
        #    return Reporter.objects.filter(Q(films__film__location__contains="Berlin") | Q(a_choice=1))

        def resolve_films(self, info, **args):
            return Film.objects.filter(
                Q(details__location__contains="Berlin") | Q(genre__in=["ot"])
            ).distinct()

    f = Film.objects.create()
    fd = FilmDetails.objects.create(location="Berlin", film=f)

    schema = graphene.Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            films {
                edges {
                    node {
                        genre
                    }
                }
            }
        }
    """

    expected = {"films": {"edges": [{"node": {"genre": "OT"}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


@pytest.mark.skipif(
    not DJANGO_FILTER_INSTALLED, reason="django-filter should be installed"
)
def test_should_query_node_multiple_filtering():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            filter_fields = ("lang", "headline")

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )
    Article.objects.create(
        headline="Article Node 1",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 2",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 3",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="en",
    )

    schema = graphene.Schema(query=Query)
    query = """
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
    """

    expected = {
        "allReporters": {
            "edges": [
                {
                    "node": {
                        "id": "UmVwb3J0ZXJUeXBlOjE=",
                        "articles": {
                            "edges": [{"node": {"id": "QXJ0aWNsZVR5cGU6MQ=="}}]
                        },
                    }
                }
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_enforce_first_or_last(graphene_settings):
    graphene_settings.RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST = True

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    schema = graphene.Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": None}

    result = schema.execute(query)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        "You must provide a `first` or `last` value to properly "
        "paginate the `allReporters` connection."
    )
    assert result.data == expected


def test_should_error_if_first_is_greater_than_max(graphene_settings):
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 100

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    assert Query.all_reporters.max_limit == 100

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    schema = graphene.Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(first: 101) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": None}

    result = schema.execute(query)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        "Requesting 101 records on the `allReporters` connection "
        "exceeds the `first` limit of 100 records."
    )
    assert result.data == expected


def test_should_error_if_last_is_greater_than_max(graphene_settings):
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 100

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    assert Query.all_reporters.max_limit == 100

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    schema = graphene.Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(last: 101) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": None}

    result = schema.execute(query)
    assert len(result.errors) == 1
    assert str(result.errors[0]) == (
        "Requesting 101 records on the `allReporters` connection "
        "exceeds the `last` limit of 100 records."
    )
    assert result.data == expected


def test_should_query_promise_connectionfields():
    from promise import Promise

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return Promise.resolve([Reporter(id=1)])

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": {"edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjE="}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_connectionfields_with_last():

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.all()

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterLastQuery {
            allReporters(last: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": {"edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjE="}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_connectionfields_with_manager():

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    r = Reporter.objects.create(
        first_name="John", last_name="NotDoe", email="johndoe@example.com", a_choice=1
    )

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType, on="doe_objects")

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.all()

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterLastQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": {"edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjE="}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_query_dataloader_fields():
    from promise import Promise
    from promise.dataloader import DataLoader

    def article_batch_load_fn(keys):
        queryset = Article.objects.filter(reporter_id__in=keys)
        return Promise.resolve(
            [
                [article for article in queryset if article.reporter_id == id]
                for id in keys
            ]
        )

    article_loader = DataLoader(article_batch_load_fn)

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            use_connection = True

        articles = DjangoConnectionField(ArticleType)

        def resolve_articles(self, info, **args):
            return article_loader.load(self.id)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    Article.objects.create(
        headline="Article Node 1",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 2",
        pub_date=datetime.date.today(),
        pub_date_time=datetime.datetime.now(),
        reporter=r,
        editor=r,
        lang="en",
    )

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        id
                        articles(first: 2) {
                            edges {
                                node {
                                    headline
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    expected = {
        "allReporters": {
            "edges": [
                {
                    "node": {
                        "id": "UmVwb3J0ZXJUeXBlOjE=",
                        "articles": {
                            "edges": [
                                {"node": {"headline": "Article Node 1"}},
                                {"node": {"headline": "Article Node 2"}},
                            ]
                        },
                    }
                }
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_handle_inherited_choices():
    class BaseModel(models.Model):
        choice_field = models.IntegerField(choices=((0, "zero"), (1, "one")))

    class ChildModel(BaseModel):
        class Meta:
            proxy = True

    class BaseType(DjangoObjectType):
        class Meta:
            model = BaseModel

    class ChildType(DjangoObjectType):
        class Meta:
            model = ChildModel

    class Query(graphene.ObjectType):
        base = graphene.Field(BaseType)
        child = graphene.Field(ChildType)

    schema = graphene.Schema(query=Query)
    query = """
        query {
          child {
            choiceField
          }
        }
    """
    result = schema.execute(query)
    assert not result.errors


def test_proxy_model_support():
    """
    This test asserts that we can query for all Reporters and proxied Reporters.
    """

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            use_connection = True

    class CNNReporterType(DjangoObjectType):
        class Meta:
            model = CNNReporter
            interfaces = (Node,)
            use_connection = True

    reporter = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    cnn_reporter = CNNReporter.objects.create(
        first_name="Some",
        last_name="Guy",
        email="someguy@cnn.com",
        a_choice=1,
        reporter_type=2,  # set this guy to be CNN
    )

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)
        cnn_reporters = DjangoConnectionField(CNNReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query ProxyModelQuery {
            allReporters {
                edges {
                    node {
                        id
                    }
                }
            }
            cnnReporters {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {
        "allReporters": {
            "edges": [
                {"node": {"id": to_global_id("ReporterType", reporter.id)}},
                {"node": {"id": to_global_id("ReporterType", cnn_reporter.id)}},
            ]
        },
        "cnnReporters": {
            "edges": [
                {"node": {"id": to_global_id("CNNReporterType", cnn_reporter.id)}}
            ]
        },
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_should_resolve_get_queryset_connectionfields():
    reporter_1 = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )
    reporter_2 = CNNReporter.objects.create(
        first_name="Some",
        last_name="Guy",
        email="someguy@cnn.com",
        a_choice=1,
        reporter_type=2,  # set this guy to be CNN
    )

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

        @classmethod
        def get_queryset(cls, queryset, info):
            return queryset.filter(reporter_type=2)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    expected = {"allReporters": {"edges": [{"node": {"id": "UmVwb3J0ZXJUeXBlOjI="}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_connection_should_limit_after_to_list_length():
    reporter_1 = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )
    reporter_2 = Reporter.objects.create(
        first_name="Some", last_name="Guy", email="someguy@cnn.com", a_choice=1
    )

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery ($after: String) {
            allReporters(first: 1 after: $after) {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    after = base64.b64encode(b"arrayconnection:10").decode()
    result = schema.execute(query, variable_values=dict(after=after))
    expected = {"allReporters": {"edges": []}}
    assert not result.errors
    assert result.data == expected


REPORTERS = [
    dict(
        first_name="First {}".format(i),
        last_name="Last {}".format(i),
        email="johndoe+{}@example.com".format(i),
        a_choice=1,
    )
    for i in range(6)
]


def test_should_return_max_limit(graphene_settings):
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 4
    reporters = [Reporter(**kwargs) for kwargs in REPORTERS]
    Reporter.objects.bulk_create(reporters)

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query AllReporters {
            allReporters {
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(query)
    assert not result.errors
    assert len(result.data["allReporters"]["edges"]) == 4


def test_should_have_next_page(graphene_settings):
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 4
    reporters = [Reporter(**kwargs) for kwargs in REPORTERS]
    Reporter.objects.bulk_create(reporters)
    db_reporters = Reporter.objects.all()

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query AllReporters($first: Int, $after: String) {
            allReporters(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                    }
                }
            }
        }
    """

    result = schema.execute(query, variable_values={})
    assert not result.errors
    assert len(result.data["allReporters"]["edges"]) == 4
    assert result.data["allReporters"]["pageInfo"]["hasNextPage"]

    last_result = result.data["allReporters"]["pageInfo"]["endCursor"]
    result2 = schema.execute(query, variable_values=dict(first=4, after=last_result))
    assert not result2.errors
    assert len(result2.data["allReporters"]["edges"]) == 2
    assert not result2.data["allReporters"]["pageInfo"]["hasNextPage"]
    gql_reporters = (
        result.data["allReporters"]["edges"] + result2.data["allReporters"]["edges"]
    )

    assert {to_global_id("ReporterType", reporter.id) for reporter in db_reporters} == {
        gql_reporter["node"]["id"] for gql_reporter in gql_reporters
    }


class TestBackwardPagination:
    def setup_schema(self, graphene_settings, max_limit):
        graphene_settings.RELAY_CONNECTION_MAX_LIMIT = max_limit
        reporters = [Reporter(**kwargs) for kwargs in REPORTERS]
        Reporter.objects.bulk_create(reporters)

        class ReporterType(DjangoObjectType):
            class Meta:
                model = Reporter
                interfaces = (Node,)

        class Query(graphene.ObjectType):
            all_reporters = DjangoConnectionField(ReporterType)

        schema = graphene.Schema(query=Query)
        return schema

    def do_queries(self, schema):
        # Simply last 3
        query_last = """
            query {
                allReporters(last: 3) {
                    edges {
                        node {
                            firstName
                        }
                    }
                }
            }
        """

        result = schema.execute(query_last)
        assert not result.errors
        assert len(result.data["allReporters"]["edges"]) == 3
        assert [
            e["node"]["firstName"] for e in result.data["allReporters"]["edges"]
        ] == ["First 3", "First 4", "First 5"]

        # Use a combination of first and last
        query_first_and_last = """
            query {
                allReporters(first: 4, last: 3) {
                    edges {
                        node {
                            firstName
                        }
                    }
                }
            }
        """

        result = schema.execute(query_first_and_last)
        assert not result.errors
        assert len(result.data["allReporters"]["edges"]) == 3
        assert [
            e["node"]["firstName"] for e in result.data["allReporters"]["edges"]
        ] == ["First 1", "First 2", "First 3"]

        # Use a combination of first and last and after
        query_first_last_and_after = """
            query queryAfter($after: String) {
                allReporters(first: 4, last: 3, after: $after) {
                    edges {
                        node {
                            firstName
                        }
                    }
                }
            }
        """

        after = base64.b64encode(b"arrayconnection:0").decode()
        result = schema.execute(
            query_first_last_and_after, variable_values=dict(after=after)
        )
        assert not result.errors
        assert len(result.data["allReporters"]["edges"]) == 3
        assert [
            e["node"]["firstName"] for e in result.data["allReporters"]["edges"]
        ] == ["First 2", "First 3", "First 4"]

    def test_should_query(self, graphene_settings):
        """
        Backward pagination should work as expected
        """
        schema = self.setup_schema(graphene_settings, max_limit=100)
        self.do_queries(schema)

    def test_should_query_with_low_max_limit(self, graphene_settings):
        """
        When doing backward pagination (using last) in combination with a max limit higher than the number of objects
        we should really retrieve the last ones.
        """
        schema = self.setup_schema(graphene_settings, max_limit=4)
        self.do_queries(schema)


def test_should_preserve_prefetch_related(django_assert_num_queries):
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (graphene.relay.Node,)

    class FilmType(DjangoObjectType):
        reporters = DjangoConnectionField(ReporterType)

        class Meta:
            model = Film
            interfaces = (graphene.relay.Node,)

    class Query(graphene.ObjectType):
        films = DjangoConnectionField(FilmType)

        def resolve_films(root, info):
            qs = Film.objects.prefetch_related("reporters")
            return qs

    r1 = Reporter.objects.create(first_name="Dave", last_name="Smith")
    r2 = Reporter.objects.create(first_name="Jane", last_name="Doe")

    f1 = Film.objects.create()
    f1.reporters.set([r1, r2])
    f2 = Film.objects.create()
    f2.reporters.set([r2])

    query = """
        query {
            films {
                edges {
                    node {
                        reporters {
                            edges {
                                node {
                                    firstName
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    schema = graphene.Schema(query=Query)
    with django_assert_num_queries(3) as captured:
        result = schema.execute(query)
    assert not result.errors


def test_should_preserve_annotations():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (graphene.relay.Node,)

    class FilmType(DjangoObjectType):
        reporters = DjangoConnectionField(ReporterType)
        reporters_count = graphene.Int()

        class Meta:
            model = Film
            interfaces = (graphene.relay.Node,)

    class Query(graphene.ObjectType):
        films = DjangoConnectionField(FilmType)

        def resolve_films(root, info):
            qs = Film.objects.prefetch_related("reporters")
            return qs.annotate(reporters_count=models.Count("reporters"))

    r1 = Reporter.objects.create(first_name="Dave", last_name="Smith")
    r2 = Reporter.objects.create(first_name="Jane", last_name="Doe")

    f1 = Film.objects.create()
    f1.reporters.set([r1, r2])
    f2 = Film.objects.create()
    f2.reporters.set([r2])

    query = """
        query {
            films {
                edges {
                    node {
                        reportersCount
                    }
                }
            }
        }
    """
    schema = graphene.Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors, str(result)

    expected = {
        "films": {
            "edges": [{"node": {"reportersCount": 2}}, {"node": {"reportersCount": 1}}]
        }
    }
    assert result.data == expected, str(result.data)


def test_connection_should_enable_offset_filtering():
    Reporter.objects.create(first_name="John", last_name="Doe")
    Reporter.objects.create(first_name="Some", last_name="Guy")

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query {
            allReporters(first: 1, offset: 1) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """

    result = schema.execute(query)
    assert not result.errors
    expected = {
        "allReporters": {"edges": [{"node": {"firstName": "Some", "lastName": "Guy"}},]}
    }
    assert result.data == expected


def test_connection_should_enable_offset_filtering_higher_than_max_limit(
    graphene_settings,
):
    graphene_settings.RELAY_CONNECTION_MAX_LIMIT = 2
    Reporter.objects.create(first_name="John", last_name="Doe")
    Reporter.objects.create(first_name="Some", last_name="Guy")
    Reporter.objects.create(first_name="Jane", last_name="Roe")
    Reporter.objects.create(first_name="Some", last_name="Lady")

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query {
            allReporters(first: 1, offset: 3) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """

    result = schema.execute(query)
    assert not result.errors
    expected = {
        "allReporters": {
            "edges": [{"node": {"firstName": "Some", "lastName": "Lady"}},]
        }
    }
    assert result.data == expected


def test_connection_should_forbid_offset_filtering_with_before():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery ($before: String) {
            allReporters(first: 1, before: $before, offset: 1) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """
    before = base64.b64encode(b"arrayconnection:2").decode()
    result = schema.execute(query, variable_values=dict(before=before))
    expected_error = "You can't provide a `before` value at the same time as an `offset` value to properly paginate the `allReporters` connection."
    assert len(result.errors) == 1
    assert result.errors[0].message == expected_error


def test_connection_should_allow_offset_filtering_with_after():
    Reporter.objects.create(first_name="John", last_name="Doe")
    Reporter.objects.create(first_name="Some", last_name="Guy")
    Reporter.objects.create(first_name="Jane", last_name="Roe")
    Reporter.objects.create(first_name="Some", last_name="Lady")

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(graphene.ObjectType):
        all_reporters = DjangoConnectionField(ReporterType)

    schema = graphene.Schema(query=Query)
    query = """
        query ReporterPromiseConnectionQuery ($after: String) {
            allReporters(first: 1, after: $after, offset: 1) {
                edges {
                    node {
                        firstName
                        lastName
                    }
                }
            }
        }
    """

    after = base64.b64encode(b"arrayconnection:0").decode()
    result = schema.execute(query, variable_values=dict(after=after))
    assert not result.errors
    expected = {
        "allReporters": {"edges": [{"node": {"firstName": "Jane", "lastName": "Roe"}},]}
    }
    assert result.data == expected
