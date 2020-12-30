import pytest

from .. import GraphQLTestCase
from ...tests.test_types import with_local_registry


@with_local_registry
def test_graphql_test_case_deprecated_client():
    """
    Test that `GraphQLTestCase._client`'s should raise pending deprecation warning.
    """

    class TestClass(GraphQLTestCase):
        GRAPHQL_SCHEMA = True

        def runTest(self):
            pass

    tc = TestClass()
    tc._pre_setup()
    tc.setUpClass()

    with pytest.warns(PendingDeprecationWarning):
        tc._client
