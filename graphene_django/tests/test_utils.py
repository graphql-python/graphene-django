import json

import pytest
from django.utils.translation import gettext_lazy
from mock import patch

from ..utils import camelize, get_model_fields, GraphQLTestCase
from .models import Film, Reporter
from ..utils.testing import graphql_query


def test_get_model_fields_no_duplication():
    reporter_fields = get_model_fields(Reporter)
    reporter_name_set = set([field[0] for field in reporter_fields])
    assert len(reporter_fields) == len(reporter_name_set)

    film_fields = get_model_fields(Film)
    film_name_set = set([field[0] for field in film_fields])
    assert len(film_fields) == len(film_name_set)


def test_camelize():
    assert camelize({}) == {}
    assert camelize("value_a") == "value_a"
    assert camelize({"value_a": "value_b"}) == {"valueA": "value_b"}
    assert camelize({"value_a": ["value_b"]}) == {"valueA": ["value_b"]}
    assert camelize({"value_a": ["value_b"]}) == {"valueA": ["value_b"]}
    assert camelize({"nested_field": {"value_a": ["error"], "value_b": ["error"]}}) == {
        "nestedField": {"valueA": ["error"], "valueB": ["error"]}
    }
    assert camelize({"value_a": gettext_lazy("value_b")}) == {"valueA": "value_b"}
    assert camelize({"value_a": [gettext_lazy("value_b")]}) == {"valueA": ["value_b"]}
    assert camelize(gettext_lazy("value_a")) == "value_a"
    assert camelize({gettext_lazy("value_a"): gettext_lazy("value_b")}) == {
        "valueA": "value_b"
    }
    assert camelize({0: {"field_a": ["errors"]}}) == {0: {"fieldA": ["errors"]}}


@pytest.mark.django_db
@patch("graphene_django.utils.testing.Client.post")
def test_graphql_test_case_op_name(post_mock):
    """
    Test that `GraphQLTestCase.query()`'s `op_name` argument produces an `operationName` field.
    """

    class TestClass(GraphQLTestCase):
        GRAPHQL_SCHEMA = True

        def runTest(self):
            pass

    tc = TestClass()
    tc.setUpClass()
    tc.query("query { }", op_name="QueryName")
    body = json.loads(post_mock.call_args.args[1])
    # `operationName` field from https://graphql.org/learn/serving-over-http/#post-request
    assert (
        "operationName",
        "QueryName",
    ) in body.items(), "Field 'operationName' is not present in the final request."


@pytest.mark.django_db
@patch("graphene_django.utils.testing.Client.post")
def test_graphql_query_case_op_name(post_mock):
    graphql_query("query { }", op_name="QueryName")
    body = json.loads(post_mock.call_args.args[1])
    # `operationName` field from https://graphql.org/learn/serving-over-http/#post-request
    assert (
        "operationName",
        "QueryName",
    ) in body.items(), "Field 'operationName' is not present in the final request."


@pytest.fixture
def client_query(client):
    def func(*args, **kwargs):
        return graphql_query(*args, client=client, **kwargs)

    return func


def test_pytest_fixture_usage(client_query):
    response = graphql_query("query { test }")
    content = json.loads(response.content)
    assert content == {"data": {"test": "Hello World"}}
