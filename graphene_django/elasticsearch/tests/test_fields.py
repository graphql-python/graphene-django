import pytest

from graphene_django.filter.tests.test_fields import assert_arguments, ArticleNode

from graphene_django.elasticsearch.tests.filters import ArticleFilterES
from graphene_django.utils import DJANGO_FILTER_INSTALLED, DJANGO_ELASTICSEARCH_DSL_INSTALLED


pytestmark = []

if DJANGO_FILTER_INSTALLED and DJANGO_ELASTICSEARCH_DSL_INSTALLED:
    from graphene_django.filter import (
        DjangoFilterConnectionField,
    )
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )

pytestmark.append(pytest.mark.django_db)


def test_filter_string_fields():
    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleFilterES)
    assert_arguments(field, "headline", "headline_term")
