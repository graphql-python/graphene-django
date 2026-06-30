import json

import pytest
from django.test import Client

from ...settings import graphene_settings
from ...tests.test_types import with_local_registry
from .. import GraphQLTestCase
from ..testing import GraphQLTestMixin


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


class _FakeHttpResponse:
    """Minimal stand-in for ``django.http.HttpResponse``.

    The ``assertResponse*`` helpers only touch ``.status_code`` and
    ``.content``, so we don't need the full Django response machinery to
    exercise them. Building this stand-in keeps the alias tests free of
    any dependency on routing, schemas, or the test client.
    """

    def __init__(self, content_dict, status_code=200):
        self.content = json.dumps(content_dict).encode("utf-8")
        self.status_code = status_code


class TestAssertionAliases:
    """Coverage for the snake_case aliases in :mod:`graphene_django.utils.testing`.

    The PR adds ``assert_response_no_errors`` /
    ``assert_response_has_errors`` as additive aliases for the existing
    camelCase ``assertResponseNoErrors`` / ``assertResponseHasErrors``.
    These tests pin three properties of that contract:

    1. The aliases must point at the **same callable** as the
       camelCase originals (no copy-paste re-implementation that could
       drift out of sync over time).
    2. The aliases must work end-to-end on a "no errors" response.
    3. The aliases must work end-to-end on a "with errors" response.

    The end-to-end checks build a tiny ``GraphQLTestCase`` subclass and
    invoke each alias against a synthesised :class:`_FakeHttpResponse`,
    so neither GraphiQL routing nor a real schema needs to be involved.
    """

    def test_alias_is_identical_to_camel_case_original(self):
        """
        Name: alias identity check
        Description: ``assert_response_no_errors`` and
            ``assert_response_has_errors`` must be the **same** function
            objects as their camelCase counterparts so behaviour cannot
            drift between spellings.
        Assumptions: Both spellings are defined on
            :class:`GraphQLTestMixin`.
        Expectations: ``is`` identity holds for both pairs.
        """
        assert (
            GraphQLTestMixin.assert_response_no_errors
            is GraphQLTestMixin.assertResponseNoErrors
        )
        assert (
            GraphQLTestMixin.assert_response_has_errors
            is GraphQLTestMixin.assertResponseHasErrors
        )

    def test_assert_response_no_errors_alias_passes_for_clean_response(self):
        """
        Name: snake_case no-errors helper, clean response
        Description: ``assert_response_no_errors`` should silently accept a
            200 response whose JSON body has no ``errors`` key, exactly
            like its camelCase counterpart.
        Assumptions: A bare ``{"data": {...}}`` body with status 200 is the
            canonical "clean" GraphQL response.
        Expectations: The call returns without raising.
        """

        class _TC(GraphQLTestCase):
            GRAPHQL_SCHEMA = True

            def runTest(self):
                pass

        tc = _TC()
        resp = _FakeHttpResponse({"data": {"hello": "world"}}, status_code=200)
        tc.assert_response_no_errors(resp)

    def test_assert_response_no_errors_alias_fails_when_errors_present(self):
        """
        Name: snake_case no-errors helper, errors present
        Description: ``assert_response_no_errors`` should fail when the
            response contains an ``errors`` key, exactly like its
            camelCase counterpart.
        Assumptions: ``unittest`` assertion failures raise
            :class:`AssertionError`.
        Expectations: ``AssertionError`` is raised.
        """

        class _TC(GraphQLTestCase):
            GRAPHQL_SCHEMA = True

            def runTest(self):
                pass

        tc = _TC()
        resp = _FakeHttpResponse(
            {"errors": [{"message": "boom"}]}, status_code=200
        )
        with pytest.raises(AssertionError):
            tc.assert_response_no_errors(resp)

    def test_assert_response_has_errors_alias_passes_when_errors_present(self):
        """
        Name: snake_case has-errors helper, errors present
        Description: ``assert_response_has_errors`` should silently accept
            a response whose body has an ``errors`` key, regardless of
            status code (GraphQL returns 200 even on errors).
        Assumptions: An ``{"errors": [...]}``-shaped response represents
            a failing GraphQL query.
        Expectations: The call returns without raising.
        """

        class _TC(GraphQLTestCase):
            GRAPHQL_SCHEMA = True

            def runTest(self):
                pass

        tc = _TC()
        resp = _FakeHttpResponse(
            {"errors": [{"message": "boom"}]}, status_code=200
        )
        tc.assert_response_has_errors(resp)

    def test_assert_response_has_errors_alias_fails_for_clean_response(self):
        """
        Name: snake_case has-errors helper, clean response
        Description: ``assert_response_has_errors`` should fail when the
            response has no ``errors`` key, exactly like its camelCase
            counterpart.
        Assumptions: ``unittest`` assertion failures raise
            :class:`AssertionError`.
        Expectations: ``AssertionError`` is raised.
        """

        class _TC(GraphQLTestCase):
            GRAPHQL_SCHEMA = True

            def runTest(self):
                pass

        tc = _TC()
        resp = _FakeHttpResponse({"data": {"hello": "world"}}, status_code=200)
        with pytest.raises(AssertionError):
            tc.assert_response_has_errors(resp)
