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

Create/Update Operations
---------------------

By default ModelSerializers accept create and update operations. To
customize this use the `model_operations` attribute. The update
operation looks up models by the primary key by default. You can
customize the look up with the lookup attribute.

Other default attributes:

`partial = False`: Accept updates without all the input fields.

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation

    class AwesomeModelMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer
            model_operations = ['create', 'update']
            lookup_field = 'id'

Overriding Update Queries
-------------------------

Use the method `get_serializer_kwargs` to override how
updates are applied.

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation

    class AwesomeModelMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer

        @classmethod
        def get_serializer_kwargs(cls, root, info, **input):
            if 'id' in input:
                instance = Post.objects.filter(id=input['id'], owner=info.context.user).first()
                if instance:
                    return {'instance': instance, 'data': input, 'partial': True}

                else:
                    raise http.Http404

            return {'data': input, 'partial': True}
