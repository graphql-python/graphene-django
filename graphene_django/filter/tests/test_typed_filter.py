import operator
from functools import reduce

import pytest
from django.db.models import Q
from django_filters import FilterSet

import graphene
from graphene.relay import Node
from graphene_django import DjangoObjectType
from graphene_django.tests.models import Article, Reporter
from graphene_django.utils import DJANGO_FILTER_INSTALLED

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    from graphene_django.filter import (
        DjangoFilterConnectionField,
        ListFilter,
        TypedFilter,
    )
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )


@pytest.fixture
def schema():
    class ArticleFilterSet(FilterSet):
        class Meta:
            model = Article
            fields = {
                "lang": ["exact", "in"],
            }

        lang__contains = TypedFilter(
            field_name="lang", lookup_expr="icontains", input_type=graphene.String
        )
        lang__in_str = ListFilter(
            field_name="lang",
            lookup_expr="in",
            input_type=graphene.List(graphene.String),
        )
        first_n = TypedFilter(input_type=graphene.Int, method="first_n_filter")
        only_first = TypedFilter(
            input_type=graphene.Boolean, method="only_first_filter"
        )
        headline_search = ListFilter(
            method="headline_search_filter",
            input_type=graphene.List(graphene.String),
        )

        def first_n_filter(self, queryset, _name, value):
            return queryset[:value]

        def only_first_filter(self, queryset, _name, value):
            if value:
                return queryset[:1]
            else:
                return queryset

        def headline_search_filter(self, queryset, _name, value):
            if not value:
                return queryset.none()
            return queryset.filter(
                reduce(operator.or_, [Q(headline__icontains=v) for v in value])
            )

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = ArticleFilterSet

    class Query(graphene.ObjectType):
        articles = DjangoFilterConnectionField(ArticleType)

    schema = graphene.Schema(query=Query)
    return schema


def test_typed_filter_schema(schema):
    """
    Check that the type provided in the filter is reflected in the schema.
    """

    schema_str = str(schema)

    filters = {
        "offset": "Int",
        "before": "String",
        "after": "String",
        "first": "Int",
        "last": "Int",
        "lang": "TestsArticleLangChoices",
        "lang_In": "[TestsArticleLangChoices]",
        "lang_Contains": "String",
        "lang_InStr": "[String]",
        "firstN": "Int",
        "onlyFirst": "Boolean",
        "headlineSearch": "[String]",
    }

    all_articles_filters = (
        schema_str.split("  articles(")[1]
        .split("): ArticleTypeConnection\n")[0]
        .split(", ")
    )

    for filter_field, gql_type in filters.items():
        assert f"{filter_field}: {gql_type}" in all_articles_filters


def test_typed_filters_work(schema):
    reporter = Reporter.objects.create(first_name="John", last_name="Doe", email="")
    Article.objects.create(headline="A", reporter=reporter, editor=reporter, lang="es")
    Article.objects.create(headline="B", reporter=reporter, editor=reporter, lang="es")
    Article.objects.create(headline="C", reporter=reporter, editor=reporter, lang="en")
    Article.objects.create(headline="AB", reporter=reporter, editor=reporter, lang="es")

    query = 'query { articles (lang_Contains: "n") { edges { node { headline } } } }'

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "C"}},
    ]

    query = "query { articles (firstN: 2) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
    ]

    query = "query { articles (onlyFirst: true) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
    ]


def test_list_filters_work(schema):
    reporter = Reporter.objects.create(first_name="John", last_name="Doe", email="")
    Article.objects.create(headline="A", reporter=reporter, editor=reporter, lang="es")
    Article.objects.create(headline="B", reporter=reporter, editor=reporter, lang="es")
    Article.objects.create(headline="C", reporter=reporter, editor=reporter, lang="en")
    Article.objects.create(headline="AB", reporter=reporter, editor=reporter, lang="es")

    query = "query { articles (lang_In: [ES]) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
    ]

    query = 'query { articles (lang_InStr: ["es"]) { edges { node { headline } } } }'

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
    ]

    query = "query { articles (lang_InStr: []) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == []

    query = "query { articles (lang_InStr: null) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
        {"node": {"headline": "C"}},
    ]

    query = 'query { articles (headlineSearch: ["a", "B"]) { edges { node { headline } } } }'

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
    ]

    query = "query { articles (headlineSearch: []) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == []

    query = "query { articles (headlineSearch: null) { edges { node { headline } } } }"

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
        {"node": {"headline": "C"}},
    ]

    query = 'query { articles (headlineSearch: [""]) { edges { node { headline } } } }'

    result = schema.execute(query)
    assert not result.errors
    assert result.data["articles"]["edges"] == [
        {"node": {"headline": "A"}},
        {"node": {"headline": "AB"}},
        {"node": {"headline": "B"}},
        {"node": {"headline": "C"}},
    ]
