import pytest
from elasticsearch_dsl.query import (
    Bool,
    Term,
    Wildcard,
    MatchPhrase,
    MatchPhrasePrefix,
    Range,
    Terms,
    Exists,
)

from graphene_django.elasticsearch.tests.commons import filter_generation
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


def test_processor_term():
    filter_generation(
        "articlesInMetaDict",
        'headlineTerm: "A text"',
        lambda mock: mock.assert_called_with(Bool(must=[Term(headline="A text")])),
    )


def test_processor_regex():
    filter_generation(
        "articlesInMetaDict",
        'headlineRegex: "A text"',
        lambda mock: mock.assert_called_with(Bool(must=[Wildcard(headline="A text")])),
    )


def test_processor_phrase():
    filter_generation(
        "articlesInMetaDict",
        'headlinePhrase: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[MatchPhrase(headline={"query": "A text"})])
        ),
    )


def test_processor_prefix():
    filter_generation(
        "articlesInMetaDict",
        'headlinePrefix: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=[MatchPhrasePrefix(headline={"query": "A text"})])
        ),
    )


def test_processor_in():
    filter_generation(
        "articlesInMetaDict",
        'headlineIn: ["A text 1", "A text 2"]',
        lambda mock: mock.assert_called_with(
            Bool(must=[Terms(headline=["A text 1", "A text 2"])])
        ),
    )


def test_processor_exits():
    filter_generation(
        "articlesInMetaDict",
        "headlineExits: true",
        lambda mock: mock.assert_called_with(
            Bool(must=[Bool(must=[Exists(field="headline")])])
        ),
    )


def test_processor_lte():
    filter_generation(
        "articlesInMetaDict",
        'headlineLte: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=Range(headline={"lte": "A text"}))
        ),
    )


def test_processor_gte():
    filter_generation(
        "articlesInMetaDict",
        'headlineGte: "A text"',
        lambda mock: mock.assert_called_with(
            Bool(must=Range(headline={"gte": "A text"}))
        ),
    )
