from graphene import ObjectType
from django_elasticsearch_dsl import DocType, Index, fields

from graphene_django.tests.models import Article, Reporter
from graphene_django.filter.tests.test_fields import ArticleNode
from graphene_django.elasticsearch.filter import filters
from graphene_django.elasticsearch.filter.fields import DjangoESFilterConnectionField
from graphene_django.elasticsearch.filter.filterset import FilterSetES

ads_index = Index("articles")


@ads_index.doc_type
class ArticleDocument(DocType):
    """Article document describing Index"""

    class Meta(object):
        """Metaclass config"""

        model = Article
        fields = ["id", "headline", "pub_date", "pub_date_time", "lang", "importance"]
        related_models = (Reporter,)

    reporter = fields.ObjectField(
        properties={
            "id": fields.IntegerField(),
            "first_name": fields.KeywordField(),
            "email": fields.KeywordField(),
        }
    )


class ArticleFilterESAsField(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        includes = []
        order_by = ["id"]

    headline = filters.StringFilterES(
        field_name="headline", lookup_expressions=["term", "contains"]
    )


class ArticleFilterESInMeta(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        includes = ["id", "headline"]
        order_by = {"id": "es_id"}


class ArticleFilterESInMetaDict(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        includes = {
            "headline": {
                "lookup_expressions": [
                    "term",
                    "contains",
                    "regex",
                    "phrase",
                    "prefix",
                    "in",
                    "exits",
                    "lte",
                    "gte",
                ]
            },
            "reporter": {},
        }


class ArticleFilterMultiField(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        includes = []

    headline = filters.StringFilterES(
        field_name="contain",
        field_name_es=["headline", "lang"],
        lookup_expressions=["contains"],
    )


class ArticleFilterGenerateAll(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        excludes = []


class ArticleFilterExcludes(FilterSetES):
    """Article Filter for ES"""

    class Meta(object):
        """Metaclass data"""

        index = ArticleDocument
        excludes = ["headline"]


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
    articles_in_generate_all = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterGenerateAll
    )
    articles_in_excludes = DjangoESFilterConnectionField(
        ArticleNode, filterset_class=ArticleFilterExcludes
    )
