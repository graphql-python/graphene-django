Graphene-Django Registry
========================

Graphene-Django uses a Registry to keep track of all the Django Models
and the ``DjangoObjectTypes`` associated to them.

This way, we make the library smart enough to convert automatically the 
relations between models to Graphene fields automatically (when possible).


get_global_registry
-------------------

By default, all model/objecttype relations will live in the global registry.

.. code:: python

    from graphene_django.registry get_global_registry

    class Reporter(DjangoObjectType):
        '''Reporter description'''
        class Meta:
            model = ReporterModel

    global_registry = get_global_registry
    global_registry.get_type_for_model(ReporterModel) # == Reporter


One Model, multiple types
-------------------------

There will be some cases where we need one Django Model to
have multiple graphene ``ObjectType``s associated to it.

.. code:: python

    from graphene_django.registry import Registry

    class Reporter(DjangoObjectType):
        '''Reporter description'''
        class Meta:
            model = ReporterModel

    class Reporter2(DjangoObjectType):
        '''Reporter2 description'''
        class Meta:
            model = ReporterModel
            skip_global_registry = True
            # We can also specify a custom registry with
            # registry = Registry()

This way, the ``ReporterModel`` could have two different types living in the same
schema.
