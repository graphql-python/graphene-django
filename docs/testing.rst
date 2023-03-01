Testing API calls with django
=============================

Using unittest
--------------

If you want to unittest your API calls derive your test case from the class `GraphQLTestCase`.

The default endpoint for testing is `/graphql`. You can override this in the `settings <https://docs.graphene-python.org/projects/django/en/latest/settings/#testing-endpoint>`__.


Usage:

.. code:: python

    import json

    from graphene_django.utils.testing import GraphQLTestCase

    class MyFancyTestCase(GraphQLTestCase):
        def test_some_query(self):
            response = self.query(
                '''
                query {
                    myModel {
                        id
                        name
                    }
                }
                ''',
                operation_name='myModel'
            )

            content = json.loads(response.content)

            # This validates the status code and if you get errors
            self.assertResponseNoErrors(response)

            # Add some more asserts if you like
            ...

        def test_query_with_variables(self):
            response = self.query(
                '''
                query myModel($id: Int!){
                    myModel(id: $id) {
                        id
                        name
                    }
                }
                ''',
                operation_name='myModel',
                variables={'id': 1}
            )

            content = json.loads(response.content)

            # This validates the status code and if you get errors
            self.assertResponseNoErrors(response)

            # Add some more asserts if you like
            ...

        def test_some_mutation(self):
            response = self.query(
                '''
                mutation myMutation($input: MyMutationInput!) {
                    myMutation(input: $input) {
                        my-model {
                            id
                            name
                        }
                    }
                }
                ''',
                operation_name='myMutation',
                input_data={'my_field': 'foo', 'other_field': 'bar'}
            )

            # This validates the status code and if you get errors
            self.assertResponseNoErrors(response)

            # Add some more asserts if you like
            ...


For testing mutations that are executed within a transaction you should subclass `GraphQLTransactionTestCase`

Usage:

.. code:: python

    import json

    from graphene_django.utils.testing import GraphQLTransactionTestCase

    class MyFancyTransactionTestCase(GraphQLTransactionTestCase):

        def test_some_mutation_that_executes_within_a_transaction(self):
            response = self.query(
                '''
                mutation myMutation($input: MyMutationInput!) {
                    myMutation(input: $input) {
                        my-model {
                            id
                            name
                        }
                    }
                }
                ''',
                operation_name='myMutation',
                input_data={'my_field': 'foo', 'other_field': 'bar'}
            )

            # This validates the status code and if you get errors
            self.assertResponseNoErrors(response)

            # Add some more asserts if you like
            ...

Using pytest
------------

To use pytest define a simple fixture using the query helper below

.. code:: python

        # Create a fixture using the graphql_query helper and `client` fixture from `pytest-django`.
        import json
        import pytest
        from graphene_django.utils.testing import graphql_query

        @pytest.fixture
        def client_query(client):
            def func(*args, **kwargs):
                return graphql_query(*args, **kwargs, client=client)

            return func

        # Test you query using the client_query fixture
        def test_some_query(client_query):
            response = client_query(
                '''
                query {
                    myModel {
                        id
                        name
                    }
                }
                ''',
                operation_name='myModel'
            )

            content = json.loads(response.content)
            assert 'errors' not in content
