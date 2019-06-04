from datetime import datetime

import pytest
from mock import mock

from graphene import Schema

from graphene_django.elasticsearch.filter import filters
from graphene_django.tests.models import Article, Reporter
from graphene_django.utils import DJANGO_FILTER_INSTALLED, DJANGO_ELASTICSEARCH_DSL_INSTALLED
from graphene_django.elasticsearch.tests.filters import ESFilterQuery, ArticleDocument

pytestmark = []

if not DJANGO_FILTER_INSTALLED or not DJANGO_ELASTICSEARCH_DSL_INSTALLED:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )

pytestmark.append(pytest.mark.django_db)


def fake_data():
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
    return a1, a2


def filter_generation(field, query_str, expected_arguments, method_to_mock="query"):
    a1, a2 = fake_data()

    query = """
    query {
        %s(%s) {
            edges {
                node {
                    headline
                }
            }
        }
    }
    """ % (field, query_str)

    mock_count = mock.Mock(return_value=3)
    mock_slice = mock.Mock(return_value=mock.Mock(to_queryset=mock.Mock(
        return_value=Article.objects.filter(pk__in=[a1.id, a2.id])
    )))
    mock_query = mock.Mock(return_value=ArticleDocument.search())

    with mock.patch('django_elasticsearch_dsl.search.Search.count', mock_count),\
         mock.patch('django_elasticsearch_dsl.search.Search.__getitem__', mock_slice),\
         mock.patch("elasticsearch_dsl.Search.%s" % method_to_mock, mock_query):

        schema = Schema(query=ESFilterQuery)
        result = schema.execute(query)

        assert not result.errors

        mock_query.assert_called_with(expected_arguments)

        assert len(result.data[field]["edges"]) == 2
        assert result.data[field]["edges"][0]["node"]["headline"] == "a1"
        assert result.data[field]["edges"][1]["node"]["headline"] == "a2"


def test_filter_as_field():
    filter_generation(
        "articlesAsField",
        "headline: \"A text\"",
        filters.StringFilterES(attr='headline').generate_es_query({"headline": "A text"}),
    )


def test_filter_as_field_order_by():
    filter_generation(
        "articlesAsField",
        "headline: \"A text\", sort:{order:desc, field:id}",
        {'id': {'order': 'desc'}},
        "sort"
    )


def test_filter_in_meta():
    filter_generation(
        "articlesInMeta",
        "headline: \"A text\"",
        filters.StringFilterES(attr='headline').generate_es_query({"headline": "A text"}),
    )


def test_filter_in_meta_dict():
    filter_generation(
        "articlesInMetaDict",
        "headline: \"A text\"",
        filters.StringFilterES(attr='headline').generate_es_query({"headline": "A text"}),
    )
