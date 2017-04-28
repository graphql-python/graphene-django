from mock import patch

from graphene import Interface, ObjectType, Schema, Mutation, String
from graphene.relay import Node
from mock import patch

from .. import registry
from ..types import DjangoObjectType, DjangoModelInput
from .models import Article as ArticleModel
from .models import Reporter as ReporterModel

registry.reset_global_registry()


class Reporter(DjangoObjectType):
    '''Reporter description'''
    class Meta:
        model = ReporterModel


class Article(DjangoObjectType):
    '''Article description'''
    class Meta:
        model = ArticleModel
        interfaces = (Node, )


class RootQuery(ObjectType):
    node = Node.Field()


schema = Schema(query=RootQuery, types=[Article, Reporter])


def test_django_interface():
    assert issubclass(Node, Interface)
    assert issubclass(Node, Node)


@patch('graphene_django.tests.models.Article.objects.get', return_value=Article(id=1))
def test_django_get_node(get):
    article = Article.get_node(1, None, None)
    get.assert_called_with(pk=1)
    assert article.id == 1


def test_django_objecttype_map_correct_fields():
    fields = Reporter._meta.fields
    fields = list(fields.keys())
    assert fields[:-2] == ['id', 'first_name', 'last_name', 'email', 'pets', 'a_choice']
    assert sorted(fields[-2:]) == ['articles', 'films']


def test_django_objecttype_with_node_have_correct_fields():
    fields = Article._meta.fields
    assert list(fields.keys()) == ['id', 'headline', 'pub_date', 'reporter', 'editor', 'lang', 'importance']


def test_schema_representation():
    expected = """
schema {
  query: RootQuery
}

type Article implements Node {
  id: ID!
  headline: String!
  pubDate: DateTime!
  reporter: Reporter!
  editor: Reporter!
  lang: ArticleLang!
  importance: ArticleImportance
}

type ArticleConnection {
  pageInfo: PageInfo!
  edges: [ArticleEdge]!
}

type ArticleEdge {
  node: Article
  cursor: String!
}

enum ArticleImportance {
  A_1
  A_2
}

enum ArticleLang {
  ES
  EN
}

scalar DateTime

interface Node {
  id: ID!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type Reporter {
  id: ID!
  firstName: String!
  lastName: String!
  email: String!
  pets: [Reporter]
  aChoice: ReporterAChoice!
  articles(before: String, after: String, first: Int, last: Int): ArticleConnection
}

enum ReporterAChoice {
  A_1
  A_2
}

type RootQuery {
  node(id: ID!): Node
}
""".lstrip()
    assert str(schema) == expected


def with_local_registry(func):
    def inner(*args, **kwargs):
        old = registry.get_global_registry()
        registry.reset_global_registry()
        try:
            retval = func(*args, **kwargs)
        except Exception as e:
            registry.registry = old
            raise e
        else:
            registry.registry = old
            return retval
    return inner


@with_local_registry
def test_django_objecttype_only_fields():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            only_fields = ('id', 'email', 'films')


    fields = list(Reporter._meta.fields.keys())
    assert fields == ['id', 'email', 'films']


@with_local_registry
def test_django_objecttype_exclude_fields():
    class Reporter(DjangoObjectType):
        class Meta:
            model = ReporterModel
            exclude_fields = ('email')


    fields = list(Reporter._meta.fields.keys())
    assert 'email' not in fields


def test_mutation_execution_with_exclude_fields():
    registry.reset_global_registry()

    class CreateReporter(Mutation):

        first_name = String()
        last_name = String()
        email = String()

        class Input(DjangoModelInput):

            class Meta:
                model = ReporterModel
                exclude_fields = ('id', 'pets', 'a_choice', 'films', 'articles')

        def mutate(self, args, context, info):
            first_name = args.get('first_name')
            last_name = args.get('last_name')
            email = args.get('email')
            return CreateReporter(first_name=first_name, last_name=last_name, email=email)

    class MyMutation(ObjectType):
        reporter_input = CreateReporter.Field()

    class Query(ObjectType):
        a = String()

    schema = Schema(query=Query, mutation=MyMutation)
    result = schema.execute(''' mutation mymutation {
        reporterInput(firstName:"Peter", lastName: "test", email: "test@test.com") {
            firstName
            lastName
            email
        }
    }
    ''')
    assert not result.errors
    assert result.data == {
        'reporterInput': {
            'firstName': 'Peter',
            'lastName': 'test',
            'email': "test@test.com"
        }
    }


def test_mutation_execution():
    registry.reset_global_registry()

    class ReporterInput(Mutation):

        first_name = String()
        last_name = String()

        class Input(DjangoModelInput):

            class Meta:
                model = ReporterModel
                only_fields = ('first_name', 'last_name')

        def mutate(self, args, context, info):
            first_name = args.get('first_name')
            last_name = args.get('last_name')
            return ReporterInput(first_name=first_name, last_name=last_name)

    class MyMutation(ObjectType):
        reporter_input = ReporterInput.Field()

    class Query(ObjectType):
        a = String()

    schema = Schema(query=Query, mutation=MyMutation)
    result = schema.execute(''' mutation mymutation {
        reporterInput(firstName:"Peter", lastName: "test") {
            firstName
            lastName
        }
    }
    ''')
    assert not result.errors
    assert result.data == {
        'reporterInput': {
            'firstName': 'Peter',
            'lastName': 'test',
        }
    }
