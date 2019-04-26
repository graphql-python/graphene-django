Installation
============

Graphene-Django takes a few seconds to install and set up.

Requirements
------------

Graphene-Django currently supports the following versions of Django:

* Django 2.X

Installation
------------

.. code:: bash

    pip install graphene-django

**We strongly recommend pinning against a specific version of Graphene-Django because new versions could introduce breaking changes to your project.**

Add ``graphene_django`` to the ``INSTALLED_APPS`` in the ``settings.py`` file of your Django project:

.. code:: python

    INSTALLED_APPS = [
        ...
        'django.contrib.staticfiles', # Required for GraphiQL
        'graphene_django'
    ]


We need to add a graphql URL to the ``urls.py`` of your Django project:

.. code:: python

    from django.conf.urls import url
    from graphene_django.views import GraphQLView

    urlpatterns = [
        # ...
        url(r'^graphql$', GraphQLView.as_view(graphiql=True)),
    ]

(Change ``graphiql=True`` to ``graphiql=False`` if you do not want to use the GraphiQL API browser.)

Finally, define the schema location for Graphene in the ``settings.py`` file of your Django project:

.. code:: python

    GRAPHENE = {
        'SCHEMA': 'django_root.schema.schema'
    }

Where ``path.schema.schema`` is the location of the ``Schema`` object in your Django project.

The most basic ``schema.py`` looks like this:

.. code:: python

    import graphene

    class Query(graphene.ObjectType):
        pass

    schema = graphene.Schema(query=Query)


To learn how to extend the schema object for your project, read the basic tutorial.