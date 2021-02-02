Fields
======

Graphene-Django provides some useful fields to help integrate Django with your GraphQL
Schema.

DjangoListField
---------------

``DjangoListField`` allows you to define a list of :ref:`DjangoObjectType<queries-objecttypes>`'s. By default it will resolve the default queryset of the Django model.

.. code:: python

   from graphene import ObjectType, Schema
   from graphene_django import DjangoListField

   class RecipeType(DjangoObjectType):
      class Meta:
         model = Recipe
         fields = ("title", "instructions")

   class Query(ObjectType):
      recipes = DjangoListField(RecipeType)

   schema = Schema(query=Query)

The above code results in the following schema definition:

.. code::

   schema {
     query: Query
   }

   type Query {
     recipes: [RecipeType!]
   }

   type RecipeType {
     title: String!
     instructions: String!
   }

Custom resolvers
****************

If your ``DjangoObjectType`` has defined a custom
:ref:`get_queryset<django-objecttype-get-queryset>` method, when resolving a
``DjangoListField`` it will be called with either the return of the field
resolver (if one is defined) or the default queryset from the Django model.

For example the following schema will only resolve recipes which have been
published and have a title:

.. code:: python

   from graphene import ObjectType, Schema
   from graphene_django import DjangoListField

   class RecipeType(DjangoObjectType):
      class Meta:
         model = Recipe
         fields = ("title", "instructions")

      @classmethod
      def get_queryset(cls, queryset, info):
         # Filter out recipes that have no title
         return queryset.exclude(title__exact="")

   class Query(ObjectType):
      recipes = DjangoListField(RecipeType)

      def resolve_recipes(parent, info):
         # Only get recipes that have been published
         return Recipe.objects.filter(published=True)

   schema = Schema(query=Query)


DjangoConnectionField
---------------------

``DjangoConnectionField`` acts similarly to ``DjangoListField`` but returns a
paginated connection following the `relay spec <https://relay.dev/graphql/connections.htm>`__
The field supports the following arguments: `first`, `last`, `offset`, `after` & `before`.
