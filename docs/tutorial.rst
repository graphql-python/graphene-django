Graphene-Django Tutorial
========================

Graphene has a number of additional features that are designed to make
working with Django *really simple*.

Note: The code in this quickstart is pulled from the `cookbook example
app <https://github.com/graphql-python/graphene-django/tree/master/examples/cookbook>`__.

Setup the Django project
------------------------

We will setup the project, create the following:

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
    pip install django
    pip install graphene_django

    # Set up a new project with a single application
    django-admin.py startproject cookbook .  # Note the trailing '.' character
    django-admin.py startapp ingredients

Now sync your database for the first time:

.. code:: bash

    python manage.py migrate

Let's create a few simple models...

Defining our models
-------------------

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
        category = models.ForeignKey(Category, related_name='ingredients')

        def __str__(self):
            return self.name

Schema
------

GraphQL presents your objects to the world as a graph structure rather
than a more hierarchical structure to which you may be accustomed. In
order to create this representation, Graphene needs to know about each
*type* of object which will appear in the graph.

This graph also has a *root type* through which all access begins. This
is the ``Query`` class below. In this example, we provide the ability to
list all ingredients via ``all_ingredients``, and the ability to obtain
a specific ingredient via ``ingredient``.

Create ``cookbook/ingredients/schema.py`` and type the following:

.. code:: python

    # cookbook/ingredients/schema.py
    from graphene import relay, ObjectType, AbstractType
    from graphene_django import DjangoObjectType
    from graphene_django.filter import DjangoFilterConnectionField

    from cookbook.ingredients.models import Category, Ingredient


    # Graphene will automatically map the Category model's fields onto the CategoryNode.
    # This is configured in the CategoryNode's Meta class (as you can see below)
    class CategoryNode(DjangoObjectType):
        class Meta:
            model = Category
            filter_fields = ['name', 'ingredients']
            filter_order_by = ['name']
            interfaces = (relay.Node, )


    class IngredientNode(DjangoObjectType):
        class Meta:
            model = Ingredient
            # Allow for some more advanced filtering here
            filter_fields = {
                'name': ['exact', 'icontains', 'istartswith'],
                'notes': ['exact', 'icontains'],
                'category': ['exact'],
                'category__name': ['exact'],
            }
            filter_order_by = ['name', 'category__name']
            interfaces = (relay.Node, )


    class Query(AbstractType):
        category = relay.Node.Field(CategoryNode)
        all_categories = DjangoFilterConnectionField(CategoryNode)

        ingredient = relay.Node.Field(IngredientNode)
        all_ingredients = DjangoFilterConnectionField(IngredientNode)


The filtering functionality is provided by
`django-filter <https://django-filter.readthedocs.org>`__. See the
`usage
documentation <https://django-filter.readthedocs.org/en/latest/usage.html#the-filter>`__
for details on the format for ``filter_fields``. While optional, this
tutorial makes use of this functionality so you will need to install
``django-filter`` for this tutorial to work:

.. code:: bash

    pip install django-filter

Note that the above ``Query`` class is marked as 'abstract'. This is
because we will now create a project-level query which will combine all
our app-level queries.

Create the parent project-level ``cookbook/schema.py``:

.. code:: python

    import graphene

    import cookbook.ingredients.schema


    class Query(cookbook.ingredients.schema.Query, graphene.ObjectType):
        # This class will inherit from multiple Queries
        # as we begin to add more apps to our project
        pass

    schema = graphene.Schema(query=Query)

You can think of this as being something like your top-level ``urls.py``
file (although it currently lacks any namespacing).

Update settings
---------------

Next, install your app and GraphiQL in your Django project. GraphiQL is
a web-based integrated development environment to assist in the writing
and executing of GraphQL queries. It will provide us with a simple and
easy way of testing our cookbook project.

Add ``ingredients`` and ``graphene_django`` to ``INSTALLED_APPS`` in ``cookbook/settings.py``:

.. code:: python

    INSTALLED_APPS = [
        ...
        # This will also make the `graphql_schema` management command available
        'graphene_django',

        # Install the ingredients app
        'ingredients',
    ]

And then add the ``SCHEMA`` to the ``GRAPHENE`` config in ``cookbook/settings.py``:

.. code:: python

    GRAPHENE = {
        'SCHEMA': 'cookbook.schema.schema'
    }

Alternatively, we can specify the schema to be used in the urls definition,
as explained below.

Creating GraphQL and GraphiQL views
-----------------------------------

Unlike a RESTful API, there is only a single URL from which GraphQL is
accessed. Requests to this URL are handled by Graphene's ``GraphQLView``
view.

This view will serve as GraphQL endpoint. As we want to have the
aforementioned GraphiQL we specify that on the params with ``graphiql=True``.

.. code:: python

    from django.conf.urls import url, include
    from django.contrib import admin

    from graphene_django.views import GraphQLView

    urlpatterns = [
        url(r'^admin/', admin.site.urls),
        url(r'^graphql', GraphQLView.as_view(graphiql=True)),
    ]


If we didn't specify the target schema in the Django settings file
as explained above, we can do so here using:

.. code:: python

    from django.conf.urls import url, include
    from django.contrib import admin

    from graphene_django.views import GraphQLView

    from cookbook.schema import schema

    urlpatterns = [
        url(r'^admin/', admin.site.urls),
        url(r'^graphql', GraphQLView.as_view(graphiql=True, schema=schema)),
    ]

Apply model changes to database
-------------------------------

Tell Django that we've added models and update the database schema to
reflect these additions.

.. code:: bash

    python manage.py makemigrations
    python manage.py migrate

Load some test data
-------------------

Now is a good time to load up some test data. The easiest option will be
to `download the
ingredients.json <https://raw.githubusercontent.com/graphql-python/graphene-django/master/examples/cookbook/cookbook/ingredients/fixtures/ingredients.json>`__
fixture and place it in
``cookbook/ingredients/fixtures/ingredients.json``. You can then run the
following:

.. code:: bash

    $ python ./manage.py loaddata ingredients

    Installed 6 object(s) from 1 fixture(s)

Alternatively you can use the Django admin interface to create some data
yourself. You'll need to run the development server (see below), and
create a login for yourself too (``./manage.py createsuperuser``).

Testing our GraphQL schema
--------------------------

We're now ready to test the API we've built. Let's fire up the server
from the command line.

.. code:: bash

    $ python ./manage.py runserver

    Performing system checks...
    Django version 1.9, using settings 'cookbook.settings'
    Starting development server at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

Go to `localhost:8000/graphiql <http://localhost:8000/graphiql>`__ and
type your first query!

.. code::

    query {
      allIngredients {
        edges {
          node {
            id,
            name
          }
        }
      }
    }

The above will return the names & IDs for all ingredients. But perhaps
you want a specific ingredient:

.. code::

    query {
      # Graphene creates globally unique IDs for all objects.
      # You may need to copy this value from the results of the first query
      ingredient(id: "SW5ncmVkaWVudE5vZGU6MQ==") {
        name
      }
    }

You can also get each ingredient for each category:

.. code::

    query {
      allCategories {
        edges {
          node {
            name,
            ingredients {
              edges {
                node {
                  name
                }
              }
            }
          }
        }
      }
    }

Or you can get only 'meat' ingredients containing the letter 'e':

.. code::

    query {
      # You can also use `category: "CATEGORY GLOBAL ID"`
      allIngredients(name_Icontains: "e", category_Name: "Meat") {
        edges {
          node {
            name
          }
        }
      }
    }
