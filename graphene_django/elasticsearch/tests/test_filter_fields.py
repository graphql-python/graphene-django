import pytest
from py.test import raises

from graphene_django.elasticsearch.filter.fields import DjangoESFilterConnectionField
from graphene_django.elasticsearch.filter.filterset import FilterSetES
from graphene_django.filter.tests.test_fields import ArticleNode
from graphene_django.elasticsearch.tests.filters import ArticleDocument
from graphene_django.utils import (
    DJANGO_FILTER_INSTALLED,
    DJANGO_ELASTICSEARCH_DSL_INSTALLED,
)

pytestmark = []

if not DJANGO_FILTER_INSTALLED or not DJANGO_ELASTICSEARCH_DSL_INSTALLED:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )

pytestmark.append(pytest.mark.django_db)


def test_filter_bad_processor():
    class ArticleFilterBadProcessor(FilterSetES):
        """Article Filter for ES"""

        class Meta(object):
            """Metaclass data"""

            index = ArticleDocument
            includes = {"headline": {"lookup_expressions": ["bad_processor"]}}

    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(
            ArticleNode, filterset_class=ArticleFilterBadProcessor
        )

    assert "bad_processor" in str(error_info.value)


def test_filter_field_without_filterset_class():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(ArticleNode)

    assert "filterset_class" in str(error_info.value)


def test_filter_field_with_fields():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(ArticleNode, fields=["headline"])

    assert "fields" in str(error_info.value)


def test_filter_field_with_order_by():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(ArticleNode, order_by=["headline"])

    assert "order_by" in str(error_info.value)


def test_filter_filterset_without_index():
    with raises(ValueError) as error_info:

        class ArticleFilterBadProcessor(FilterSetES):
            """Article Filter for ES"""

            class Meta(object):
                """Metaclass data"""

        DjangoESFilterConnectionField(
            ArticleNode, filterset_class=ArticleFilterBadProcessor
        )

    assert "Index in Meta" in str(error_info.value)


def test_filter_filterset_without_xcludes():
    with raises(ValueError) as error_info:

        class ArticleFilterBadProcessor(FilterSetES):
            """Article Filter for ES"""

            class Meta(object):
                """Metaclass data"""

                index = ArticleDocument

        DjangoESFilterConnectionField(
            ArticleNode, filterset_class=ArticleFilterBadProcessor
        )

    assert "includes or excludes field in Meta" in str(error_info.value)
