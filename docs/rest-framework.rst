Integration with Django Rest Framework
======================================

You can re-use your Django Rest Framework serializer with
graphene django.


Mutation
--------

You can create a Mutation based on a serializer by using the
`SerializerMutation` base class:

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation

    class MyAwesomeMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

