from datetime import datetime

from mock import mock

from graphene import Schema

from graphene_django.tests.models import Article, Reporter
from graphene_django.elasticsearch.tests.filters import ESFilterQuery, ArticleDocument


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


def generate_query(field, query_str):
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
    """ % (
        field,
        query_str,
    )
    return query


def filter_generation(field, query_str, verify_arguments, method_to_mock="query"):
    a1, a2 = fake_data()

    query = generate_query(field, query_str)

    mock_count = mock.Mock(return_value=3)
    mock_slice = mock.Mock(
        return_value=mock.Mock(
            to_queryset=mock.Mock(
                return_value=Article.objects.filter(pk__in=[a1.id, a2.id])
            )
        )
    )
    mock_query = mock.Mock(return_value=ArticleDocument.search())

    with mock.patch(
        "django_elasticsearch_dsl.search.Search.count", mock_count
    ), mock.patch(
        "django_elasticsearch_dsl.search.Search.__getitem__", mock_slice
    ), mock.patch(
        "elasticsearch_dsl.Search.%s" % method_to_mock, mock_query
    ):
        schema = Schema(query=ESFilterQuery)
        result = schema.execute(query)

        assert not result.errors

        verify_arguments(mock_query)

        assert len(result.data[field]["edges"]) == 2
        assert result.data[field]["edges"][0]["node"]["headline"] == "a1"
        assert result.data[field]["edges"][1]["node"]["headline"] == "a2"
