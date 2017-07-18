from django import forms
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


def test_model_form():
    class PetMutation(ModelFormMutation):
        class Meta:
            form_class = PetForm

    assert PetMutation.model == Pet
    assert PetMutation.return_field_name == 'pet'
