Introspection Schema
====================

Relay uses `Babel Relay
Plugin <https://facebook.github.io/relay/docs/guides-babel-plugin.html>`__
that requires you to provide your GraphQL schema data.

Graphene comes with a management command for Django to dump your schema
data to ``schema.json`` that is compatible with babel-relay-plugin.

Usage
-----

Include ``graphene_django`` to ``INSTALLED_APPS`` in you project
settings:

.. code:: python

    INSTALLED_APPS += ('graphene_django')

Assuming your Graphene schema is at ``tutorial.quickstart.schema``, run
the command:

.. code:: bash

    ./manage.py graphql_schema --schema tutorial.quickstart.schema --out schema.json

It dumps your full introspection schema to ``schema.json`` inside your
project root directory. Point ``babel-relay-plugin`` to this file and
you're ready to use Relay with Graphene GraphQL implementation.

Advanced Usage
--------------

To simplify the command to ``./manage.py graphql_schema``, you can
specify the parameters in your settings.py:

.. code:: python

    GRAPHENE = {
    	'SCHEMA': 'tutorial.quickstart.schema',
    	'SCHEMA_OUTPUT': 'data/schema.json'  # defaults to schema.json
    }


Running ``./manage.py graphql_schema`` dumps your schema to
``<project root>/data/schema.json``.

Help
----

Run ``./manage.py graphql_schema -h`` for command usage.
