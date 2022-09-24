Django Debug Middleware
=======================

You can debug your GraphQL queries in a similar way to
`django-debug-toolbar <https://django-debug-toolbar.readthedocs.org/>`__,
but outputting in the results in GraphQL response as fields, instead of
the graphical HTML interface. Exceptions with their stack traces are also exposed.

For that, you will need to add the plugin in your graphene schema.

Installation
------------

For use the Django Debug plugin in Graphene:

* Add ``graphene_django.debug.DjangoDebugMiddleware`` into ``MIDDLEWARE`` in the ``GRAPHENE`` settings.

* Add the ``debug`` field into the schema root ``Query`` with the value ``graphene.Field(DjangoDebug, name='_debug')``.


.. code:: python

    from graphene_django.debug import DjangoDebug

    class Query(graphene.ObjectType):
        # ...
        debug = graphene.Field(DjangoDebug, name='_debug')

    schema = graphene.Schema(query=Query)


And in your ``settings.py``:

.. code:: python

    GRAPHENE = {
        ...
        'MIDDLEWARE': [
            'graphene_django.debug.DjangoDebugMiddleware',
        ]
    }

Querying
--------

You can query it for outputting all the sql transactions that happened in
the GraphQL request, like:

.. code::

    {
      # A example that will use the ORM for interact with the DB
      allIngredients {
        edges {
          node {
            id,
            name
          }
        }
      }
      # Here is the debug field that will output the SQL queries
      _debug {
        sql {
          rawSql
        }
        exceptions {
          message
          stack
        }
      }
    }

Note that the ``_debug`` field must be the last field in your query.
