Schema
======

The ``graphene.Schema`` object describes your data model and provides a GraphQL server with an associated set of resolve methods that know how to fetch data. The most basic schema you can create looks like this:

.. code:: python

    import graphene

    class Query(graphene.ObjectType):
        pass

    class Mutation(graphene.ObjectType):
        pass

    schema = graphene.Schema(query=Query, mutation=Mutation)


This schema doesn't do anything yet, but it is ready to accept new Query or Mutation fields.


Adding to the schema
--------------------

If you have defined a ``Query`` or ``Mutation``, you can register them with the schema:

.. code:: python

    import graphene

    import my_app.schema.Query
    import my_app.schema.Mutation

    class Query(
        my_app.schema.Query, # Add your Query objects here
        graphene.ObjectType
    ):
        pass

    class Mutation(
        my_app.schema.Mutation, # Add your Mutation objects here
        graphene.ObjectType
    ):
        pass

    schema = graphene.Schema(query=Query, mutation=Mutation)

You can add as many mixins to the base ``Query`` and ``Mutation`` objects as you like.

Read more about Schema on the `core graphene docs <https://docs.graphene-python.org/en/latest/types/schema/>`__