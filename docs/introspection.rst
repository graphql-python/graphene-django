Introspection Schema
====================

Relay Modern uses `Babel Relay Plugin <https://facebook.github.io/relay/docs/en/installation-and-setup>`__ which requires you to provide your GraphQL schema data.

Graphene comes with a Django management command to dump your schema
data to ``schema.json`` which is compatible with babel-relay-plugin.

Usage
-----

Include ``graphene_django`` to ``INSTALLED_APPS`` in your project
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

The schema file is sorted to create a reproducible canonical representation.

GraphQL SDL Representation
--------------------------

The schema can also be exported as a GraphQL SDL file by changing the file
extension :

.. code:: bash

    ./manage.py graphql_schema --schema tutorial.quickstart.schema --out schema.graphql

When exporting the schema as a ``.graphql`` file the ``--indent`` option is
ignored.


Advanced Usage
--------------

The ``--indent`` option can be used to specify the number of indentation spaces to
be used in the output. Defaults to `None` which displays all data on a single line.

The ``--watch`` option can be used to run ``./manage.py graphql_schema`` in watch mode, where it will automatically output a new schema every time there are file changes in your project

To simplify the command to ``./manage.py graphql_schema``, you can
specify the parameters in your settings.py:

.. code:: python

    GRAPHENE = {
        'SCHEMA': 'tutorial.quickstart.schema',
        'SCHEMA_OUTPUT': 'data/schema.json',  # defaults to schema.json,
        'SCHEMA_INDENT': 2,  # Defaults to None (displays all data on a single line)
    }


Running ``./manage.py graphql_schema`` dumps your schema to
``<project root>/data/schema.json``.

Help
----

Run ``./manage.py graphql_schema -h`` for command usage.
