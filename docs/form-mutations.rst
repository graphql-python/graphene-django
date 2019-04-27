Integration with Django forms
=============================

Graphene-Django comes with mutation classes that will convert the fields on Django forms into inputs on a mutation.
*Note: the API is experimental and will likely change in the future.*

DjangoFormMutation
------------------

.. code:: python

    from graphene_django.forms.mutation import DjangoFormMutation

    class MyForm(forms.Form):
        name = forms.CharField()

    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

``MyMutation`` will automatically receive an ``input`` argument. This argument should be a ``dict`` where the key is ``name`` and the value is a string.

DjangoModelFormMutation
-----------------------

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
---------------

Form mutations will call ``is_valid()`` on your forms.

If the form is valid then the class method ``perform_mutate(form, info)`` is called on the mutation. Override this method
to change how the form is saved or to return a different Graphene object type.

If the form is *not* valid then a list of errors will be returned. These errors have two fields: ``field``, a string
containing the name of the invalid form field, and ``messages``, a list of strings with the validation messages.
