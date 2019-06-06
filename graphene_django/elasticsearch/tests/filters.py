from graphene import ObjectType
from django_elasticsearch_dsl import DocType, Index

from graphene_django.tests.models import Article
from graphene_django.filter.tests.test_fields import ArticleNode
from graphene_django.elasticsearch.filter import filters
from graphene_django.elasticsearch.filter.fields import DjangoESFilterConnectionField
from graphene_django.elasticsearch.filter.filterset import FilterSetES

ads_index = Index('articles')


@ads_index.doc_type
class ArticleDocument(DocType):
    """Article document describing Index"""
    class Meta(object):
        """Metaclass config"""
        model = Article
        fields = [
            'headline',
        ]


class ArticleFilterESAsField(FilterSetES):
    """Article Filter for ES"""
    class Meta(object):
        """Metaclass data"""
        index = ArticleDocument
        includes = []
        order_by = ['id']

    headline = filters.StringFilterES(field_name='headline', lookup_expressions=['term', 'contains'])


class ArticleFilterESInMeta(FilterSetES):
    """Article Filter for ES"""
    class Meta(object):
        """Metaclass data"""
        index = ArticleDocument
        includes = ['headline']


class ArticleFilterESInMetaDict(FilterSetES):
    """Article Filter for ES"""
    class Meta(object):
        """Metaclass data"""
        index = ArticleDocument
        includes = {
            'headline': {
                'lookup_expressions': ['term', 'contains']
            }
        }


class ArticleFilterMultiField(FilterSetES):
    """Article Filter for ES"""
    class Meta(object):
        """Metaclass data"""
        index = ArticleDocument
        includes = []

    headline = filters.StringFilterES(
        field_name='contain',
        field_name_es=['headline', 'lang'],
        lookup_expressions=['contains']
    )


class ESFilterQuery(ObjectType):
    """A query for ES fields"""
    articles_as_field = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterESAsField
    )
    articles_in_meta = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterESInMeta
    )
    articles_in_meta_dict = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterESInMetaDict
    )
    articles_in_multi_field = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterMultiField
    )
