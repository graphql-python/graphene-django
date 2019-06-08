from datetime import datetime

import pytest
from py.test import raises
from mock import mock

from elasticsearch_dsl.query import Bool, Match, Term, Wildcard, MatchPhrase, MatchPhrasePrefix, Range, Terms, Exists
from graphene import Schema, ObjectType

from graphene_django.elasticsearch.filter.fields import DjangoESFilterConnectionField
from graphene_django.elasticsearch.filter.filterset import FilterSetES
from graphene_django.filter.tests.test_fields import ArticleNode
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
    """ % (field, query_str)
    return query


def filter_generation(field, query_str, expected_arguments, method_to_mock="query"):
    a1, a2 = fake_data()

    query = generate_query(field, query_str)

    mock_count = mock.Mock(return_value=3)
    mock_slice = mock.Mock(return_value=mock.Mock(to_queryset=mock.Mock(
        return_value=Article.objects.filter(pk__in=[a1.id, a2.id])
    )))
    mock_query = mock.Mock(return_value=ArticleDocument.search())

    with mock.patch('django_elasticsearch_dsl.search.Search.count', mock_count), \
         mock.patch('django_elasticsearch_dsl.search.Search.__getitem__', mock_slice), \
         mock.patch("elasticsearch_dsl.Search.%s" % method_to_mock, mock_query):
        schema = Schema(query=ESFilterQuery)
        result = schema.execute(query)

        assert not result.errors

        mock_query.assert_called_with(expected_arguments)

        assert len(result.data[field]["edges"]) == 2
        assert result.data[field]["edges"][0]["node"]["headline"] == "a1"
        assert result.data[field]["edges"][1]["node"]["headline"] == "a2"


def test_filter_string():
    filter_generation(
        "articlesAsField",
        "headline: \"A text\"",
        Bool(must=[Match(headline={'query': 'A text', 'fuzziness': 'auto'})]),
    )


def test_filter_string_date():
    filter_generation(
        "articlesAsField",
        "headline: \"A text\"",
        Bool(must=[Match(headline={'query': 'A text', 'fuzziness': 'auto'})]),
    )


def test_filter_as_field_order_by():
    filter_generation(
        "articlesAsField",
        "headline: \"A text\", sort:{order:desc, field:id}",
        {'id': {'order': 'desc'}},
        "sort"
    )


def test_filter_as_field_order_by_dict():
    filter_generation(
        "articlesInMeta",
        "headline: \"A text\", sort:{order:desc, field:id}",
        {'es_id': {'order': 'desc'}},
        "sort"
    )


def test_filter_in_meta():
    filter_generation(
        "articlesInMeta",
        "headline: \"A text\"",
        Bool(must=[Match(headline={'query': 'A text', 'fuzziness': 'auto'})]),
    )


def test_filter_in_meta_dict():
    filter_generation(
        "articlesInMetaDict",
        "headline: \"A text\"",
        Bool(must=[Match(headline={'query': 'A text', 'fuzziness': 'auto'})]),
    )


def test_filter_in_meta_dict_foreign():
    filter_generation(
        "articlesInMetaDict",
        "reporterEamail: \"A mail\"",
        Bool(must=[Match(reporter__email={'query': 'A mail', 'fuzziness': 'auto'})]),
    )


def test_filter_in_multi_field():
    filter_generation(
        "articlesInMultiField",
        "contain: \"A text\"",
        Bool(must=[Bool(should=[
            Match(headline={'query': 'A text', 'fuzziness': 'auto'}),
            Match(lang={'query': 'A text', 'fuzziness': 'auto'})
        ])]),
    )


def test_filter_generating_all():
    filter_generation(
        "articlesInGenerateAll",
        "headline: \"A text\", "
        "pubDate: \"0000-00-00\", "
        "pubDateTime: \"00:00:00\", "
        "lang: \"es\", "
        "importance: 1, ",
        Bool(must=[
            Match(headline={'query': 'A text', 'fuzziness': 'auto'}),
            Match(pub_date={'query': '0000-00-00', 'fuzziness': 'auto'}),
            Match(pub_date_time={'query': '00:00:00', 'fuzziness': 'auto'}),
            Match(lang={'query': 'es', 'fuzziness': 'auto'}),
            Term(importance=1)
        ]),
    )


def test_filter_generating_exclude():
    query = generate_query("articlesInExcludes", "headline: \"A text\", ")

    schema = Schema(query=ESFilterQuery)
    result = schema.execute(query)

    assert len(result.errors) > 0


def test_filter_bad_processor():
    class ArticleFilterBadProcessor(FilterSetES):
        """Article Filter for ES"""

        class Meta(object):
            """Metaclass data"""
            index = ArticleDocument
            includes = {
                'headline': {
                    'lookup_expressions': ['bad_processor']
                }
            }

    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(
            ArticleNode, filterset_class=ArticleFilterBadProcessor
        )

    assert "bad_processor" in str(error_info.value)


def test_filter_field_without_filterset_class():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(
            ArticleNode
        )

    assert "filterset_class" in str(error_info.value)


def test_filter_field_with_fields():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(
            ArticleNode, fields=['headline']
        )

    assert "fields" in str(error_info.value)


def test_filter_field_with_order_by():
    with raises(ValueError) as error_info:
        DjangoESFilterConnectionField(
            ArticleNode, order_by=['headline']
        )

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


def test_processor_term():
    filter_generation(
        "articlesInMetaDict",
        "headlineTerm: \"A text\"",
        Bool(must=[Term(headline='A text')]),
    )


def test_processor_regex():
    filter_generation(
        "articlesInMetaDict",
        "headlineRegex: \"A text\"",
        Bool(must=[Wildcard(headline='A text')]),
    )


def test_processor_phrase():
    filter_generation(
        "articlesInMetaDict",
        "headlinePhrase: \"A text\"",
        Bool(must=[MatchPhrase(headline={'query': 'A text'})]),
    )


def test_processor_prefix():
    filter_generation(
        "articlesInMetaDict",
        "headlinePrefix: \"A text\"",
        Bool(must=[MatchPhrasePrefix(headline={'query': 'A text'})]),
    )


def test_processor_in():
    filter_generation(
        "articlesInMetaDict",
        "headlineIn: [\"A text 1\", \"A text 2\"]",
        Bool(must=[Terms(headline=['A text 1', 'A text 2'])]),
    )


def test_processor_exits():
    filter_generation(
        "articlesInMetaDict",
        "headlineExits: true",
        Bool(must=[Bool(must=[Exists(field='headline')])]),
    )


def test_processor_lte():
    filter_generation(
        "articlesInMetaDict",
        "headlineLte: \"A text\"",
        Bool(must=Range(headline={'lte': 'A text'})),
    )


def test_processor_gte():
    filter_generation(
        "articlesInMetaDict",
        "headlineGte: \"A text\"",
        Bool(must=Range(headline={'gte': 'A text'})),
    )
