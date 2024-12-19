Settings
========

Graphene-Django can be customised using settings. This page explains each setting and their defaults.

Usage
-----

Add settings to your Django project by creating a Dictionary with name ``GRAPHENE`` in the project's ``settings.py``:

.. code:: python

    GRAPHENE = {
        ...
    }


``SCHEMA``
----------

The location of the top-level ``Schema`` class.

Default: ``None``

.. code:: python

    GRAPHENE = {
        'SCHEMA': 'path.to.schema.schema',
    }


``SCHEMA_OUTPUT``
-----------------

The name of the file where the GraphQL schema output will go.

Default: ``schema.json``

.. code:: python

    GRAPHENE = {
        'SCHEMA_OUTPUT': 'schema.json',
    }


``SCHEMA_INDENT``
-----------------

The indentation level of the schema output.

Default: ``2``

.. code:: python

    GRAPHENE = {
        'SCHEMA_INDENT': 2,
    }


``MIDDLEWARE``
--------------

A tuple of middleware that will be executed for each GraphQL query.

See the `middleware documentation <https://docs.graphene-python.org/en/latest/execution/middleware/>`__ for more information.

Default: ``()``

.. code:: python

    GRAPHENE = {
        'MIDDLEWARE': (
            'path.to.my.middleware.class',
        ),
    }


``RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST``
------------------------------------------

Enforces relay queries to have the ``first`` or ``last`` argument.

Default: ``False``

.. code:: python

    GRAPHENE = {
        'RELAY_CONNECTION_ENFORCE_FIRST_OR_LAST': False,
    }


``RELAY_CONNECTION_MAX_LIMIT``
------------------------------

The maximum size of objects that can be requested through a relay connection.

Default: ``100``

.. code:: python

    GRAPHENE = {
        'RELAY_CONNECTION_MAX_LIMIT': 100,
    }


``CAMELCASE_ERRORS``
--------------------

When set to ``True`` field names in the ``errors`` object will be camel case.
By default they will be snake case.

Default: ``False``

.. code:: python

   GRAPHENE = {
      'CAMELCASE_ERRORS': False,
   }

   # result = schema.execute(...)
   print(result.errors)
   # [
   #     {
   #         'field': 'test_field',
   #         'messages': ['This field is required.'],
   #     }
   # ]

.. code:: python

   GRAPHENE = {
      'CAMELCASE_ERRORS': True,
   }

   # result = schema.execute(...)
   print(result.errors)
   # [
   #     {
   #         'field': 'testField',
   #         'messages': ['This field is required.'],
   #     }
   # ]


``DJANGO_CHOICE_FIELD_ENUM_CONVERT``
--------------------------------------

When set to ``True`` Django choice fields are automatically converted into Enum types.

Can be disabled globally by setting it to ``False``.

Default: ``True``

``DJANGO_CHOICE_FIELD_ENUM_V2_NAMING``
--------------------------------------

Set to ``True`` to use the old naming format for the auto generated Enum types from Django choice fields. The old format looks like this: ``{object_name}_{field_name}``

Default: ``False``


``DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME``
----------------------------------------

Define the path of a function that takes the Django choice field and returns a string to completely customise the naming for the Enum type.

If set to a function then the ``DJANGO_CHOICE_FIELD_ENUM_V2_NAMING`` setting is ignored.

Default: ``None``

.. code:: python

   # myapp.utils
   def enum_naming(field):
      if isinstance(field.model, User):
         return f"CustomUserEnum{field.name.title()}"
      return f"CustomEnum{field.name.title()}"

   GRAPHENE = {
      'DJANGO_CHOICE_FIELD_ENUM_CUSTOM_NAME': "myapp.utils.enum_naming"
   }


``SUBSCRIPTION_PATH``
---------------------

Define an alternative URL path where subscription operations should be routed.

The GraphiQL interface will use this setting to intelligently route subscription operations. This is useful if you have more advanced infrastructure requirements that prevent websockets from being handled at the same path (e.g., a WSGI server listening at ``/graphql`` and an ASGI server listening at ``/ws/graphql``).

Default: ``None``

.. code:: python

   GRAPHENE = {
      'SUBSCRIPTION_PATH': "/ws/graphql"
   }


``GRAPHIQL_HEADER_EDITOR_ENABLED``
----------------------------------

GraphiQL starting from version 1.0.0 allows setting custom headers in similar fashion to query variables.

Set to ``False`` if you want to disable GraphiQL headers editor tab for some reason.

This setting is passed to ``headerEditorEnabled`` GraphiQL options, for details refer to GraphiQLDocs_.

Default: ``True``

.. code:: python

   GRAPHENE = {
      'GRAPHIQL_HEADER_EDITOR_ENABLED': True,
   }


``TESTING_ENDPOINT``
--------------------

Define the graphql endpoint url used for the `GraphQLTestCase` class.

Default: ``/graphql``

.. code:: python

   GRAPHENE = {
      'TESTING_ENDPOINT': '/customEndpoint'
   }


``GRAPHIQL_SHOULD_PERSIST_HEADERS``
-----------------------------------

Set to ``True`` if you want to persist GraphiQL headers after refreshing the page.

This setting is passed to ``shouldPersistHeaders`` GraphiQL options, for details refer to GraphiQLDocs_.


Default: ``False``

.. code:: python

   GRAPHENE = {
      'GRAPHIQL_SHOULD_PERSIST_HEADERS': False,
   }


``GRAPHIQL_INPUT_VALUE_DEPRECATION``
------------------------------------

Set to ``True`` if you want GraphiQL to show any deprecated fields on input object types' docs.

For example, having this schema:

.. code:: python

    class MyMutationInputType(graphene.InputObjectType):
        old_field = graphene.String(deprecation_reason="You should now use 'newField' instead.")
        new_field = graphene.String()

    class MyMutation(graphene.Mutation):
        class Arguments:
            input = types.MyMutationInputType()

GraphiQL will add a ``Show Deprecated Fields`` button to toggle information display on ``oldField`` and its deprecation
reason. Otherwise, you would get neither a button nor any information at all on ``oldField``.

This setting is passed to ``inputValueDeprecation`` GraphiQL options, for details refer to GraphiQLDocs_.

Default: ``False``

.. code:: python

   GRAPHENE = {
      'GRAPHIQL_INPUT_VALUE_DEPRECATION': False,
   }


.. _GraphiQLDocs: https://graphiql-test.netlify.app/typedoc/modules/graphiql_react#graphiqlprovider-2


``MAX_VALIDATION_ERRORS``
------------------------------------

In case ``validation_rules`` are provided to ``GraphQLView``, if this is set to a non-negative ``int`` value,
``graphql.validation.validate`` will stop validation after this number of errors has been reached.
If not set or set to ``None``, the maximum number of errors will follow ``graphql.validation.validate`` default
*i.e.* 100.

Default: ``None``
