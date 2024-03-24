Basic Tutorial
===========================================

Graphene Django has a number of additional features that are designed to make
working with Django easy. Our primary focus in this tutorial is to give a good
understanding of how to connect models from Django ORM to Graphene object types.

Set up the Django project
-------------------------

We will set up the project, create the following:

-  A Django project called ``cookbook``
-  An app within ``cookbook`` called ``ingredients``

.. code:: bash

    # Create the project directory
    mkdir cookbook
    cd cookbook

    # Create a virtualenv to isolate our package dependencies locally
    virtualenv env
    source env/bin/activate  # On Windows use `env\Scripts\activate`

    # Install Django and Graphene with Django support
    pip install django graphene_django

    # Set up a new project with a single application
    django-admin startproject cookbook .  # Note the trailing '.' character
    cd cookbook
    django-admin startapp ingredients

Now sync your database for the first time:

.. code:: bash

    cd ..
    python manage.py migrate

Let's create a few simple models...

Defining our models
^^^^^^^^^^^^^^^^^^^

Let's get started with these models:

.. code:: python

    # cookbook/ingredients/models.py
    from django.db import models

    class Category(models.Model):
        name = models.CharField(max_length=100)

        def __str__(self):
            return self.name

    class Ingredient(models.Model):
        name = models.CharField(max_length=100)
        notes = models.TextField()
        category = models.ForeignKey(
            Category, related_name="ingredients", on_delete=models.CASCADE
        )

        def __str__(self):
            return self.name

Add ingredients as INSTALLED_APPS:

.. code:: python

    # cookbook/settings.py

    INSTALLED_APPS = [
        ...
        # Install the ingredients app
        "cookbook.ingredients",
    ]

Make sure the app name in ``cookbook.ingredients.apps.IngredientsConfig`` is set to ``cookbook.ingredients``.

.. code:: python

    # cookbook/ingredients/apps.py

    from django.apps import AppConfig


    class IngredientsConfig(AppConfig):
        default_auto_field = 'django.db.models.BigAutoField'
        name = 'cookbook.ingredients'

Don't forget to create & run migrations:

.. code:: bash

    python manage.py makemigrations
    python manage.py migrate


Load some test data
^^^^^^^^^^^^^^^^^^^

Now is a good time to load up some test data. The easiest option will be
to `download the
ingredients.json <https://raw.githubusercontent.com/graphql-python/graphene-django/main/examples/cookbook/cookbook/ingredients/fixtures/ingredients.json>`__
fixture and place it in
``cookbook/ingredients/fixtures/ingredients.json``. You can then run the
following:

.. code:: bash

    python manage.py loaddata ingredients

    Installed 6 object(s) from 1 fixture(s)

Alternatively you can use the Django admin interface to create some data
yourself. You'll need to run the development server (see below), and
create a login for yourself too (``python manage.py createsuperuser``).

Register models with admin panel:

.. code:: python

    # cookbook/ingredients/admin.py
    from django.contrib import admin
    from cookbook.ingredients.models import Category, Ingredient

    admin.site.register(Category)
    admin.site.register(Ingredient)


Hello GraphQL - Schema and Object Types
---------------------------------------

In order to make queries to our Django project, we are going to need few things:

* Schema with defined object types
* A view, taking queries as input and returning the result

GraphQL presents your objects to the world as a graph structure rather
than a more hierarchical structure to which you may be accustomed. In
order to create this representation, Graphene needs to know about each
*type* of object which will appear in the graph.

This graph also has a *root type* through which all access begins. This
is the ``Query`` class below.

To create GraphQL types for each of our Django models, we are going to subclass the ``DjangoObjectType`` class which will automatically define GraphQL fields that correspond to the fields on the Django models.

After we've done that, we will list those types as fields in the ``Query`` class.

Create ``cookbook/schema.py`` and type the following:

.. code:: python

    # cookbook/schema.py
    import graphene
    from graphene_django import DjangoObjectType

    from cookbook.ingredients.models import Category, Ingredient

    class CategoryType(DjangoObjectType):
        class Meta:
            model = Category
            fields = ("id", "name", "ingredients")

    class IngredientType(DjangoObjectType):
        class Meta:
            model = Ingredient
            fields = ("id", "name", "notes", "category")

    class Query(graphene.ObjectType):
        all_ingredients = graphene.List(IngredientType)
        category_by_name = graphene.Field(CategoryType, name=graphene.String(required=True))

        def resolve_all_ingredients(root, info):
            # We can easily optimize query count in the resolve method
            return Ingredient.objects.select_related("category").all()

        def resolve_category_by_name(root, info, name):
            try:
                return Category.objects.get(name=name)
            except Category.DoesNotExist:
                return None

    schema = graphene.Schema(query=Query)

You can think of this as being something like your top-level ``urls.py``
file.

Testing everything so far
-------------------------

We are going to do some configuration work, in order to have a working Django where we can test queries, before we move on, updating our schema.

Update settings
^^^^^^^^^^^^^^^

Next, install your app and GraphiQL in your Django project. GraphiQL is
a web-based integrated development environment to assist in the writing
and executing of GraphQL queries. It will provide us with a simple and
easy way of testing our cookbook project.

Add ``graphene_django`` to ``INSTALLED_APPS`` in ``cookbook/settings.py``:

.. code:: python

    # cookbook/settings.py

    INSTALLED_APPS = [
        ...
        "graphene_django",
    ]

And then add the ``SCHEMA`` to the ``GRAPHENE`` config in ``cookbook/settings.py``:

.. code:: python

    # cookbook/settings.py

    GRAPHENE = {
        "SCHEMA": "cookbook.schema.schema"
    }

Alternatively, we can specify the schema to be used in the urls definition,
as explained below.

Creating GraphQL and GraphiQL views
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Unlike a RESTful API, there is only a single URL from which GraphQL is
accessed. Requests to this URL are handled by Graphene's ``GraphQLView``
view.

This view will serve as GraphQL endpoint. As we want to have the
aforementioned GraphiQL we specify that on the parameters with ``graphiql=True``.

.. code:: python

    # cookbook/urls.py

    from django.contrib import admin
    from django.urls import path
    from django.views.decorators.csrf import csrf_exempt

    from graphene_django.views import GraphQLView

    urlpatterns = [
        path("admin/", admin.site.urls),
        path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    ]


If we didn't specify the target schema in the Django settings file
as explained above, we can do so here using:

.. code:: python

    # cookbook/urls.py

    from django.contrib import admin
    from django.urls import path
    from django.views.decorators.csrf import csrf_exempt

    from graphene_django.views import GraphQLView

    from cookbook.schema import schema

    urlpatterns = [
        path("admin/", admin.site.urls),
        path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True, schema=schema))),
    ]



Testing our GraphQL schema
^^^^^^^^^^^^^^^^^^^^^^^^^^

We're now ready to test the API we've built. Let's fire up the server
from the command line.

.. code:: bash

    python manage.py runserver

    Performing system checks...
    Django version 3.0.7, using settings 'cookbook.settings'
    Starting development server at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

Go to `localhost:8000/graphql <http://localhost:8000/graphql>`__ and
type your first query!

.. code::

    query {
      allIngredients {
        id
        name
      }
    }

If you are using the provided fixtures, you will see the following response:

.. code::

    {
      "data": {
        "allIngredients": [
          {
            "id": "1",
            "name": "Eggs"
          },
          {
            "id": "2",
            "name": "Milk"
          },
          {
            "id": "3",
            "name": "Beef"
          },
          {
            "id": "4",
            "name": "Chicken"
          }
        ]
      }
    }


Congratulations, you have created a working GraphQL server 🥳!

Note: Graphene `automatically camelcases <http://docs.graphene-python.org/en/latest/types/schema/#auto-camelcase-field-names>`__ all field names for better compatibility with JavaScript clients.


Getting relations
-----------------

Using the current schema we can query for relations too. This is where GraphQL becomes really powerful!

For example, we may want to get a specific categories and list all ingredients that are in that category.

We can do that with the following query:

.. code::

    query {
      categoryByName(name: "Dairy") {
        id
        name
        ingredients {
          id
          name
        }
      }
    }

This will give you (in case you are using the fixtures) the following result:

.. code::

    {
      "data": {
        "categoryByName": {
          "id": "1",
          "name": "Dairy",
          "ingredients": [
            {
              "id": "1",
              "name": "Eggs"
            },
            {
              "id": "2",
              "name": "Milk"
            }
          ]
        }
      }
    }

We can also list all ingredients and get information for the category they are in:

.. code::

    query {
      allIngredients {
        id
        name
        category {
          id
          name
        }
      }
    }

Summary
-------

As you can see, GraphQL is very powerful and integrating Django models allows you to get started with a working server quickly.

If you want to put things like ``django-filter`` and automatic pagination in action, you should continue with the :ref:`Relay tutorial`.

A good idea is to check the `Graphene <http://docs.graphene-python.org/en/latest/>`__
documentation so that you are familiar with it as well.
