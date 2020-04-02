Testing API calls with django
=============================

If you want to unittest your API calls derive your test case from the class `GraphQLTestCase`.

Your endpoint is set through the `GRAPHQL_URL` attribute on `GraphQLTestCase`. The default endpoint is `GRAPHQL_URL = "/graphql/"`.

Usage:

.. code:: python

    import json

    from graphene_django.utils.testing import GraphQLTestCase
    from my_project.config.schema import schema

    class MyFancyTestCase(GraphQLTestCase):
        # Here you need to inject your test case's schema
        GRAPHQL_SCHEMA = schema

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
                op_name='myModel'
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
                op_name='myModel',
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
                op_name='myMutation',
                input_data={'my_field': 'foo', 'other_field': 'bar'}
            )

            # This validates the status code and if you get errors
            self.assertResponseNoErrors(response)

            # Add some more asserts if you like
            ...
