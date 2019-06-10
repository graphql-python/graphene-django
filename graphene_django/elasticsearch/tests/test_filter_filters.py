import pytest
from elasticsearch_dsl.query import Bool, Match, Term
from graphene import Schema

from graphene_django.elasticsearch.tests.commons import (
    filter_generation,
    generate_query,
)
from graphene_django.elasticsearch.tests.filters import ESFilterQuery
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


def test_filter_string():
    filter_generation(
        "articlesAsField",
        'headline: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[Match(headline={"query": "A text", "fuzziness": "auto"})])
        ),
    )


def test_filter_string_date():
    filter_generation(
        "articlesAsField",
        'headline: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[Match(headline={"query": "A text", "fuzziness": "auto"})])
        ),
    )


def test_filter_as_field_order_by():
    filter_generation(
        "articlesAsField",
        'headline: "A text", sort:{order:desc, field:id}',
        lambda mock: mock.assert_called_with({"id": {"order": "desc"}}),
        "sort",
    )


def test_filter_as_field_order_by_dict():
    filter_generation(
        "articlesInMeta",
        'headline: "A text", sort:{order:desc, field:id}',
        lambda mock: mock.assert_called_with({"es_id": {"order": "desc"}}),
        "sort",
    )


def test_filter_in_meta():
    filter_generation(
        "articlesInMeta",
        'headline: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[Match(headline={"query": "A text", "fuzziness": "auto"})])
        ),
    )


def test_filter_in_meta_dict():
    filter_generation(
        "articlesInMetaDict",
        'headline: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[Match(headline={"query": "A text", "fuzziness": "auto"})])
        ),
    )


def test_filter_in_meta_dict_foreign():
    filter_generation(
        "articlesInMetaDict",
        'reporterEmail: "A mail"',
        lambda mock: mock.assert_called_with(
            Bool(must=[Match(reporter__email={"query": "A mail", "fuzziness": "auto"})])
        ),
    )


def test_filter_in_multi_field():
    filter_generation(
        "articlesInMultiField",
        'contain: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(
                must=[
                    Bool(
                        should=[
                            Match(headline={"query": "A text", "fuzziness": "auto"}),
                            Match(lang={"query": "A text", "fuzziness": "auto"}),
                        ]
                    )
                ]
            )
        ),
    )


def compare_must_array(must, other_must):
    assert len(must) == len(other_must)

    for target in must:
        assert target in other_must


def test_filter_generating_all():
    spected_query = Bool(
        must=[
            Match(headline={"query": "A text", "fuzziness": "auto"}),
            Match(pub_date={"query": "0000-00-00", "fuzziness": "auto"}),
            Match(pub_date_time={"query": "00:00:00", "fuzziness": "auto"}),
            Match(lang={"query": "es", "fuzziness": "auto"}),
            Term(importance=1),
        ]
    )

    filter_generation(
        "articlesInGenerateAll",
        'headline: "A text", '
        'pubDate: "0000-00-00", '
        'pubDateTime: "00:00:00", '
        'lang: "es", '
        "importance: 1, ",
        lambda mock: compare_must_array(mock.call_args[0][0].must, spected_query.must),
    )


def test_filter_generating_exclude():
    query = generate_query("articlesInExcludes", 'headline: "A text", ')

    schema = Schema(query=ESFilterQuery)
    result = schema.execute(query)

    assert len(result.errors) > 0
