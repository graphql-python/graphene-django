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


Customizing the mutation
--------

By default, when the serializer is instantiated, only the input argument
is passed. Sometimes, the Django `request` object is required in the serializer
context. In fact, any sort of complicated serializer will probably require something
like `request.user`. This can be performed by customizing the instantiation
method as such:

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation

    class MySecondAwesomeMutation(SerializerMutation):
        
        @classmethod
        def instantiate_serializer(cls, instance, args, request, info):
            
            input = args.get('input')
            
            return cls._meta.serializer_class(data=dict(input),
                                              context={'request': request})
      
        class Meta:
            serializer_class = MySerializer
