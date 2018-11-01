Custom errors
=============

Default GraphQL error format similar to the following snippet

.. code:: json

    {
      "errors": [
        {
          "message": "Variable \"$myAwesomeField\" of required type \"String!\" was not provided.",
          "locations": [
            {
              "line": 1,
              "column": 13
            }
          ]
        }
      ]
    }

And there is a way customise it by swapping default ``GraphQLView`` with your own
and then override ``format_error`` method

.. code:: python

    class MyGraphQLView(GraphQLView):
        @staticmethod
        def format_error(error) -> Dict[str, Any]:
            if isinstance(error, GraphQLError):
                return format_error(error)

            return GraphQLView.format_error(error)


Here is custom formatting function

.. code:: python

  def format_error(error: GraphQLError) -> Dict[str, Any]:
      """Extract field from ``error`` and return formatted error
      :param error: GraphQLError
      :return: mapping of fieldName -> error message
      """
      formatted_error = {
          n.variable.name.value: str(error)
          for n in error.nodes
      }

      if error.path:
          formatted_error["path"] = error.path

      return formatted_error


.. note::
  ``error.nodes`` might be other GraphQL type as well.
