from datetime import date
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
import graphene

from ..fields import DjangoConnectionField, DjangoListField
from ..optimization import optimize_queryset
from ..types import DjangoObjectType
from .models import (
    Article as ArticleModel,
    Reporter as ReporterModel
)


class Article(DjangoObjectType):
    class Meta:
        model = ArticleModel
        interfaces = (graphene.relay.Node,)


class Reporter(DjangoObjectType):
    favorite_pet = graphene.Field(lambda: Reporter)

    class Meta:
        model = ReporterModel
        #interfaces = (graphene.relay.Node,)
        optimizations = {
            'favorite_pet': {
                'prefetch': ['pets']
            }
        }

    def resolve_favorite_pet(self, *args):
        for pet in self.pets.all():
            if pet.last_name == 'Kent':
                return pet


class RootQuery(graphene.ObjectType):
    article = graphene.Field(Article, id=graphene.ID())
    articles = DjangoConnectionField(Article)
    reporters = DjangoListField(Reporter)

    def resolve_article(self, args, context, info):
        qs = ArticleModel.objects
        qs = optimize_queryset(ArticleModel, qs, info.field_asts[0])
        return qs.get(**args)

    def resolve_reporters(self, args, context, info):
        return ReporterModel.objects


schema = graphene.Schema(query=RootQuery)


class TestOptimization(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.reporter = ReporterModel.objects.create(
            first_name='Clark', last_name='Kent',
            email='ckent@dailyplanet.com', a_choice='this'
        )
        cls.editor = ReporterModel.objects.create(
            first_name='Perry', last_name='White',
            email='pwhite@dailyplanet.com', a_choice='this'
        )
        cls.article = ArticleModel.objects.create(
            headline='Superman Saves the Day',
            pub_date=date.today(),
            reporter=cls.reporter,
            editor=cls.editor
        )
        cls.other_article = ArticleModel.objects.create(
            headline='Lex Luthor is SO Rich',
            pub_date=date.today(),
            reporter=cls.reporter,
            editor=cls.editor
        )
        cls.editor.pets.add(cls.reporter)

    def test_select_related(self):
        query = """query GetArticle($articleId: ID!){
          article(id: $articleId) {
              headline
              reporter {
                email
              }
              editor {
                email
              }
          }
        }"""

        variables = {'articleId': str(self.article.id)}

        with CaptureQueriesContext(connection) as query_context:
            results = schema.execute(query, variable_values=variables)

        returned_article = results.data['article']
        assert returned_article['headline'] == self.article.headline
        assert returned_article['reporter']['email'] == self.reporter.email
        assert returned_article['editor']['email'] == self.editor.email

        self.assertEqual(len(query_context.captured_queries), 1)

    def test_prefetch_related(self):
        query = """query {
          articles {
            edges {
              node {
                headline
                editor {
                  email
                  pets {
                    email
                  }
                }
              }
            }
          }
        }"""

        with CaptureQueriesContext(connection) as query_context:
            results = schema.execute(query)

        returned_articles = results.data['articles']['edges']
        assert len(returned_articles) == 2

        self.assertEqual(len(query_context.captured_queries), 4)

    def test_manual(self):
        query = """query {
          reporters {
            email
            favoritePet {
              email
            }
          }
        }"""

        with CaptureQueriesContext(connection) as query_context:
            results = schema.execute(query)

        returned_reporters = results.data['reporters']
        assert len(returned_reporters) == 2

        returned_editor = [reporter for reporter in returned_reporters
                           if reporter['email'] == self.editor.email][0]
        assert returned_editor['favoritePet']['email'] == self.reporter.email

        self.assertEqual(len(query_context.captured_queries), 2)
