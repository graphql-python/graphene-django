from datetime import datetime

import pytest
from mock import mock

from graphene import Schema
from graphene_django.tests.models import Article, Reporter
from graphene_django.filter.tests.test_fields import assert_arguments, ArticleNode
from graphene_django.utils import DJANGO_FILTER_INSTALLED, DJANGO_ELASTICSEARCH_DSL_INSTALLED
from graphene_django.elasticsearch.tests.filters import ArticleFilterES, ESFilterQuery


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


def test_filter_query():
    r1 = Reporter.objects.create(first_name="r1", last_name="r1", email="r1@test.com")

    a1 = Article.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    a2 = Article.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )

    query = """
    query {
        articles {
            edges {
                node {
                    headline
                }
            }
        }
    }
    """

    mock_count = mock.Mock(return_value=3)
    mock_slice = mock.Mock(return_value=mock.Mock(to_queryset=mock.Mock(
        return_value=Article.objects.filter(pk__in=[a1.id, a2.id])
    )))

    with mock.patch('django_elasticsearch_dsl.search.Search.count', mock_count),\
         mock.patch('django_elasticsearch_dsl.search.Search.__getitem__', mock_slice):

        schema = Schema(query=ESFilterQuery)
        result = schema.execute(query)

        assert not result.errors

        assert len(result.data["articles"]["edges"]) == 2
        assert result.data["articles"]["edges"][0]["node"]["headline"] == "a1"
        assert result.data["articles"]["edges"][1]["node"]["headline"] == "a2"
