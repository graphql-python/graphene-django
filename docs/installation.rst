Installation
============

Graphene-Django takes a few seconds to install and set up.

Requirements
------------

Graphene-Django currently supports the following versions of Django:

* >= Django 2.2

Installation
------------

.. code:: bash

    pip install graphene-django

**We strongly recommend pinning against a specific version of Graphene-Django because new versions could introduce breaking changes to your project.**

Add ``graphene_django`` to the ``INSTALLED_APPS`` in the ``settings.py`` file of your Django project:

.. code:: python

    INSTALLED_APPS = [
        ...
        "django.contrib.staticfiles", # Required for GraphiQL
        "graphene_django"
    ]


We need to add a ``graphql`` URL to the ``urls.py`` of your Django project:

For Django 2.2 and above:

.. code:: python

    from django.urls import path
    from graphene_django.views import GraphQLView

    urlpatterns = [
        # ...
        path("graphql", GraphQLView.as_view(graphiql=True)),
    ]

(Change ``graphiql=True`` to ``graphiql=False`` if you do not want to use the GraphiQL API browser.)

Finally, define the schema location for Graphene in the ``settings.py`` file of your Django project:

.. code:: python

    GRAPHENE = {
        "SCHEMA": "django_root.schema.schema"
    }

Where ``path.schema.schema`` is the location of the ``Schema`` object in your Django project.

The most basic ``schema.py`` looks like this:

.. code:: python

    import graphene

    class Query(graphene.ObjectType):
        hello = graphene.String(default_value="Hi!")

    schema = graphene.Schema(query=Query)


To learn how to extend the schema object for your project, read the basic tutorial.

CSRF exempt
-----------

If you have enabled `CSRF protection <https://docs.djangoproject.com/en/3.0/ref/csrf/>`_ in your Django app
you will find that it prevents your API clients from POSTing to the ``graphql`` endpoint. You can either
update your API client to pass the CSRF token with each request (the Django docs have a guide on how to do that: https://docs.djangoproject.com/en/3.0/ref/csrf/#ajax) or you can exempt your Graphql endpoint from CSRF protection by wrapping the ``GraphQLView`` with the ``csrf_exempt``
decorator:

.. code:: python

    # urls.py

    from django.urls import path
    from django.views.decorators.csrf import csrf_exempt

    from graphene_django.views import GraphQLView

    urlpatterns = [
        # ...
        path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    ]
