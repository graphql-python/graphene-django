import pytest
from django.test import Client

from ...settings import graphene_settings
from ...tests.test_types import with_local_registry
from .. import GraphQLTestCase


@with_local_registry
def test_graphql_test_case_deprecated_client_getter():
    """
    `GraphQLTestCase._client`' getter should raise pending deprecation warning.
    """

    class TestClass(GraphQLTestCase):
        GRAPHQL_SCHEMA = True

        def runTest(self):
            pass

    tc = TestClass()
    tc._pre_setup()
    tc.setUpClass()

    with pytest.warns(PendingDeprecationWarning):
        tc._client  # noqa: B018


@with_local_registry
def test_graphql_test_case_deprecated_client_setter():
    """
    `GraphQLTestCase._client`' setter should raise pending deprecation warning.
    """

    class TestClass(GraphQLTestCase):
        GRAPHQL_SCHEMA = True

        def runTest(self):
            pass

    tc = TestClass()
    tc._pre_setup()
    tc.setUpClass()

    with pytest.warns(PendingDeprecationWarning):
        tc._client = Client()


def test_graphql_test_case_imports_endpoint():
    """
    GraphQLTestCase class should import the default endpoint from settings file
    """

    assert GraphQLTestCase.GRAPHQL_URL == graphene_settings.TESTING_ENDPOINT
