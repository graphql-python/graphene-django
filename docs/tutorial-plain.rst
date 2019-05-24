Basic Tutorial
===========================================

Graphene Django has a number of additional features that are designed to make
working with Django easy. Our primary focus in this tutorial is to give a good
understanding of how to connect models from Django ORM to graphene object types.

Set up the Django project
-------------------------

You can find the entire project in ``examples/cookbook-plain``.

----

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
    pip install django
    pip install graphene_django

    # Set up a new project with a single application
    django-admin.py startproject cookbook .  # Note the trailing '.' character
    cd cookbook
    django-admin.py startapp ingredients

Now sync your database for the first time:

.. code:: bash

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
            Category, related_name='ingredients', on_delete=models.CASCADE)

        def __str__(self):
            return self.name

Add ingredients as INSTALLED_APPS:

.. code:: python

    INSTALLED_APPS = [
        ...
        # Install the ingredients app
        'cookbook.ingredients',
    ]


Don't forget to create & run migrations:

.. code:: bash

    python manage.py makemigrations
    python manage.py migrate


Load some test data
^^^^^^^^^^^^^^^^^^^

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

This means, for each of our models, we are going to create a type, subclassing ``DjangoObjectType``

After we've done that, we will list those types as fields in the ``Query`` class.

Create ``cookbook/ingredients/schema.py`` and type the following:

.. code:: python

    # cookbook/ingredients/schema.py
    import graphene

    from graphene_django.types import DjangoObjectType

    from cookbook.ingredients.models import Category, Ingredient


    class CategoryType(DjangoObjectType):
        class Meta:
            model = Category


    class IngredientType(DjangoObjectType):
        class Meta:
            model = Ingredient


    class Query(object):
        all_categories = graphene.List(CategoryType)
        all_ingredients = graphene.List(IngredientType)

        def resolve_all_categories(self, info, **kwargs):
            return Category.objects.all()

        def resolve_all_ingredients(self, info, **kwargs):
            # We can easily optimize query count in the resolve method
            return Ingredient.objects.select_related('category').all()


Note that the above ``Query`` class is a mixin, inheriting from
``object``. This is because we will now create a project-level query
class which will combine all our app-level mixins.

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

    INSTALLED_APPS = [
        ...
        # This will also make the `graphql_schema` management command available
        'graphene_django',
    ]

And then add the ``SCHEMA`` to the ``GRAPHENE`` config in ``cookbook/settings.py``:

.. code:: python

    GRAPHENE = {
        'SCHEMA': 'cookbook.schema.schema'
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

    from django.conf.urls import url, include
    from django.contrib import admin

    from graphene_django.views import GraphQLView

    urlpatterns = [
        url(r'^admin/', admin.site.urls),
        url(r'^graphql$', GraphQLView.as_view(graphiql=True)),
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
        url(r'^graphql$', GraphQLView.as_view(graphiql=True, schema=schema)),
    ]



Testing our GraphQL schema
^^^^^^^^^^^^^^^^^^^^^^^^^^

We're now ready to test the API we've built. Let's fire up the server
from the command line.

.. code:: bash

    $ python ./manage.py runserver

    Performing system checks...
    Django version 1.9, using settings 'cookbook.settings'
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

You can experiment with ``allCategories`` too.

Something to have in mind is the `auto camelcasing <http://docs.graphene-python.org/en/latest/types/schema/#auto-camelcase-field-names>`__ that is happening.


Getting relations
-----------------

Right now, with this simple setup in place, we can query for relations too. This is where graphql becomes really powerful!

For example, we may want to list all categories and in each category, all ingredients that are in that category.

We can do that with the following query:

.. code::

    query {
      allCategories {
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
        "allCategories": [
          {
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
          },
          {
            "id": "2",
            "name": "Meat",
            "ingredients": [
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
        ]
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

Getting single objects
----------------------

So far, we have been able to fetch list of objects and follow relation. But what about single objects?

We can update our schema to support that, by adding new query for ``ingredient`` and ``category`` and adding arguments, so we can query for specific objects.

.. code:: python

  import graphene

  from graphene_django.types import DjangoObjectType

  from cookbook.ingredients.models import Category, Ingredient


  class CategoryType(DjangoObjectType):
      class Meta:
          model = Category


  class IngredientType(DjangoObjectType):
      class Meta:
          model = Ingredient


  class Query(object):
      category = graphene.Field(CategoryType,
                                id=graphene.Int(),
                                name=graphene.String())
      all_categories = graphene.List(CategoryType)


      ingredient = graphene.Field(IngredientType,
                                  id=graphene.Int(),
                                  name=graphene.String())
      all_ingredients = graphene.List(IngredientType)

      def resolve_all_categories(self, info, **kwargs):
          return Category.objects.all()

      def resolve_all_ingredients(self, info, **kwargs):
          return Ingredient.objects.all()

      def resolve_category(self, info, **kwargs):
          id = kwargs.get('id')
          name = kwargs.get('name')

          if id is not None:
              return Category.objects.get(pk=id)

          if name is not None:
              return Category.objects.get(name=name)

          return None

      def resolve_ingredient(self, info, **kwargs):
          id = kwargs.get('id')
          name = kwargs.get('name')

          if id is not None:
              return Ingredient.objects.get(pk=id)

          if name is not None:
              return Ingredient.objects.get(name=name)

          return None

Now, with the code in place, we can query for single objects.

For example, lets query ``category``:


.. code::

    query {
      category(id: 1) {
        name
      }
      anotherCategory: category(name: "Dairy") {
        ingredients {
          id
          name
        }
      }
    }

This will give us the following results:

.. code::

    {
      "data": {
        "category": {
          "name": "Dairy"
        },
        "anotherCategory": {
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

As an exercise, you can try making some queries to ``ingredient``.

Something to keep in mind - since we are using one field several times in our query, we need `aliases <http://graphql.org/learn/queries/#aliases>`__


Summary
-------

As you can see, GraphQL is very powerful but there are a lot of repetitions in our example. We can do a lot of improvements by adding layers of abstraction on top of ``graphene-django``.

If you want to put things like ``django-filter`` and automatic pagination in action, you should continue with the **relay tutorial.**

A good idea is to check the `graphene <http://docs.graphene-python.org/en/latest/>`__
documentation but it is not essential to understand and use Graphene-Django in your project.