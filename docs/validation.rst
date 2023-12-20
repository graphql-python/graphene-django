Query Validation
================

Graphene-Django supports query validation by allowing passing a list of validation rules (subclasses of `ValidationRule <https://github.com/graphql-python/graphql-core/blob/v3.2.3/src/graphql/validation/rules/__init__.py>`_ from graphql-core) to the ``validation_rules`` option in ``GraphQLView``.

.. code:: python

    from django.urls import path
    from graphene.validation import DisableIntrospection
    from graphene_django.views import GraphQLView

    urlpatterns = [
        path("graphql", GraphQLView.as_view(validation_rules=(DisableIntrospection,))),
    ]

or

.. code:: python

    from django.urls import path
    from graphene.validation import DisableIntrospection
    from graphene_django.views import GraphQLView

    class View(GraphQLView):
        validation_rules = (DisableIntrospection,)

    urlpatterns = [
        path("graphql", View.as_view()),
    ]
