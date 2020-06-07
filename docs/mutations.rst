Mutations
=========

Introduction
------------

Graphene-Django makes it easy to perform mutations.

With Graphene-Django we can take advantage of pre-existing Django features to
quickly build CRUD functionality, while still using the core `graphene mutation <https://docs.graphene-python.org/en/latest/types/mutations/>`__
features to add custom mutations to a Django project.

Simple example
--------------

.. code:: python

    import graphene

    from graphene_django import DjangoObjectType

    from .models import Question


    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = '__all__'


    class QuestionMutation(graphene.Mutation):
        class Arguments:
            # The input arguments for this mutation
            text = graphene.String(required=True)
            id = graphene.ID()

        # The class attributes define the response of the mutation
        question = graphene.Field(QuestionType)

        def mutate(self, info, text, id):
            question = Question.objects.get(pk=id)
            question.text = text
            question.save()
            # Notice we return an instance of this mutation
            return QuestionMutation(question=question)


    class Mutation(graphene.ObjectType):
        update_question = QuestionMutation.Field()


Django Forms
------------

Graphene-Django comes with mutation classes that will convert the fields on Django forms into inputs on a mutation.

DjangoFormMutation
~~~~~~~~~~~~~~~~~~

.. code:: python

    from graphene_django.forms.mutation import DjangoFormMutation

    class MyForm(forms.Form):
        name = forms.CharField()

    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

``MyMutation`` will automatically receive an ``input`` argument. This argument should be a ``dict`` where the key is ``name`` and the value is a string.

DjangoModelFormMutation
~~~~~~~~~~~~~~~~~~~~~~~

``DjangoModelFormMutation`` will pull the fields from a ``ModelForm``.

.. code:: python

    from graphene_django.forms.mutation import DjangoModelFormMutation

    class Pet(models.Model):
        name = models.CharField()

    class PetForm(forms.ModelForm):
        class Meta:
            model = Pet
            fields = ('name',)

    # This will get returned when the mutation completes successfully
    class PetType(DjangoObjectType):
        class Meta:
            model = Pet
            fields = '__all__'

    class PetMutation(DjangoModelFormMutation):
        pet = Field(PetType)

        class Meta:
            form_class = PetForm

``PetMutation`` will grab the fields from ``PetForm`` and turn them into inputs. If the form is valid then the mutation
will lookup the ``DjangoObjectType`` for the ``Pet`` model and return that under the key ``pet``. Otherwise it will
return a list of errors.

You can change the input name (default is ``input``) and the return field name (default is the model name lowercase).

.. code:: python

    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm
            input_field_name = 'data'
            return_field_name = 'my_pet'

Form validation
~~~~~~~~~~~~~~~

Form mutations will call ``is_valid()`` on your forms.

If the form is valid then the class method ``perform_mutate(form, info)`` is called on the mutation. Override this method
to change how the form is saved or to return a different Graphene object type.

If the form is *not* valid then a list of errors will be returned. These errors have two fields: ``field``, a string
containing the name of the invalid form field, and ``messages``, a list of strings with the validation messages.


Django REST Framework
---------------------

You can re-use your Django Rest Framework serializer with Graphene Django mutations.

You can create a Mutation based on a serializer by using the `SerializerMutation` base class:

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation

    class MyAwesomeMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer


Create/Update Operations
~~~~~~~~~~~~~~~~~~~~~~~~

By default ModelSerializers accept create and update operations. To
customize this use the `model_operations` attribute on the ``SerializerMutation`` class.

The update operation looks up models by the primary key by default. You can
customize the look up with the ``lookup_field`` attribute on the ``SerializerMutation`` class.

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation
    from .serializers import MyModelSerializer


    class AwesomeModelMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer
            model_operations = ['create', 'update']
            lookup_field = 'id'

Overriding Update Queries
~~~~~~~~~~~~~~~~~~~~~~~~~

Use the method ``get_serializer_kwargs`` to override how updates are applied.

.. code:: python

    from graphene_django.rest_framework.mutation import SerializerMutation
    from .serializers import MyModelSerializer


    class AwesomeModelMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer

        @classmethod
        def get_serializer_kwargs(cls, root, info, **input):
            if 'id' in input:
                instance = Post.objects.filter(
                    id=input['id'], owner=info.context.user
                ).first()
                if instance:
                    return {'instance': instance, 'data': input, 'partial': True}

                else:
                    raise http.Http404

            return {'data': input, 'partial': True}



Relay
-----

You can use relay with mutations. A Relay mutation must inherit from
``ClientIDMutation`` and implement the ``mutate_and_get_payload`` method:

.. code:: python

    import graphene
    from graphene import relay
    from graphene_django import DjangoObjectType
    from graphql_relay import from_global_id

    from .queries import QuestionType


    class QuestionMutation(relay.ClientIDMutation):
        class Input:
            text = graphene.String(required=True)
            id = graphene.ID()

        question = graphene.Field(QuestionType)

        @classmethod
        def mutate_and_get_payload(cls, root, info, text, id):
            question = Question.objects.get(pk=from_global_id(id)[1])
            question.text = text
            question.save()
            return QuestionMutation(question=question)

Notice that the ``class Arguments`` is renamed to ``class Input`` with relay.
This is due to a deprecation of ``class Arguments`` in graphene 2.0.

Relay ClientIDMutation accept a ``clientIDMutation`` argument.
This argument is also sent back to the client with the mutation result
(you do not have to do anything). For services that manage
a pool of many GraphQL requests in bulk, the ``clientIDMutation``
allows you to match up a specific mutation with the response.
