from django import forms
from django.test import TestCase
from py.test import raises

from graphene_django.tests.models import Pet
from ..mutation import FormMutation, ModelFormMutation


class MyForm(forms.Form):
    text = forms.CharField()


class PetForm(forms.ModelForm):

    class Meta:
        model = Pet
        fields = ('name',)


def test_needs_form_class():
    with raises(Exception) as exc:
        class MyMutation(FormMutation):
            pass

    assert exc.value.args[0] == 'Missing form_class'


def test_has_fields():
    class MyMutation(FormMutation):
        class Meta:
            form_class = MyForm

    assert 'errors' in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(FormMutation):
        class Meta:
            form_class = MyForm

    assert 'text' in MyMutation.Input._meta.fields


class ModelFormMutationTests(TestCase):

    def test_model_form_mutation(self):
        class PetMutation(ModelFormMutation):
            class Meta:
                form_class = PetForm

        self.assertEqual(PetMutation.model, Pet)
        self.assertEqual(PetMutation.return_field_name, 'pet')

    def test_model_form_mutation_mutate(self):
        class PetMutation(ModelFormMutation):
            class Meta:
                form_class = PetForm

        PetMutation.mutate(None, {'input': {'name': 'Fluffy'}}, None, None)

        self.assertEqual(Pet.objects.count(), 1)
        pet = Pet.objects.get()
        self.assertEqual(pet.name, 'Fluffy')
