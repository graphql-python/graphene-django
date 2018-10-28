import pytest

from django import forms
from django.test import TestCase

from graphene import NonNull, List

from graphene_django.tests.models import Pet, Film, FilmDetails
from ..mutation import DjangoFormMutation, DjangoModelFormMutation


class MyForm(forms.Form):
    text = forms.CharField()


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = '__all__'


def test_needs_form_class():
    with pytest.raises(Exception) as exc:
        class MyMutation(DjangoFormMutation):
            pass

    assert exc.value.args[0] == "form_class is required for DjangoFormMutation"


def test_has_output_fields():
    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    assert "text" in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    assert "text" in MyMutation.Input._meta.fields


def test_default_meta_fields():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm

    assert PetMutation._meta.model == Pet
    assert PetMutation._meta.return_field_name == "pet"

    assert "pet" in PetMutation._meta.fields


def test_default_input_meta_fields():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm

    assert PetMutation._meta.model == Pet
    assert PetMutation._meta.return_field_name == "pet"

    assert "name" in PetMutation.Input._meta.fields
    assert "client_mutation_id" in PetMutation.Input._meta.fields
    assert "id" in PetMutation.Input._meta.fields


def test_exclude_fields_input_meta_fields():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm
            exclude_fields = ['id']

    assert PetMutation._meta.model == Pet
    assert PetMutation._meta.return_field_name == "pet"
    assert "name" in PetMutation.Input._meta.fields
    assert "age" in PetMutation.Input._meta.fields
    assert "client_mutation_id" in PetMutation.Input._meta.fields
    assert "id" not in PetMutation.Input._meta.fields


def test_return_field_name_is_camelcased():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm
            model = FilmDetails

    assert PetMutation._meta.model == FilmDetails
    assert PetMutation._meta.return_field_name == "filmDetails"


def test_custom_return_field_name():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm
            model = Film
            return_field_name = "animal"

    assert PetMutation._meta.model == Film
    assert PetMutation._meta.return_field_name == "animal"
    assert "animal" in PetMutation._meta.fields


@pytest.mark.django_db
def test_model_form_mutation_mutate():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm

    pet = Pet.objects.create(name="Axel", age=10)

    result = PetMutation.mutate_and_get_payload(None, None, id=pet.pk, name="Mia", age=10)

    assert Pet.objects.count() == 1
    pet.refresh_from_db()
    assert pet.name == "Mia"
    assert result.errors == {}


@pytest.mark.django_db
def test_model_form_mutation_updates_existing():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm

    result = PetMutation.mutate_and_get_payload(None, None, name="Mia", age=10)

    assert Pet.objects.count() == 1
    pet = Pet.objects.get()
    assert pet.name == "Mia"
    assert pet.age == 10
    assert result.errors == {}


@pytest.mark.django_db
def test_model_form_mutation_mutate_invalid_form():
    class PetMutation(DjangoModelFormMutation):
        class Meta:
            form_class = PetForm

    result = PetMutation.mutate_and_get_payload(None, None)

    # A pet was not created
    assert Pet.objects.count() == 0

    assert result.errors != {}

    assert result.errors.name == ["This field is required."]
    assert result.errors.age == ["This field is required."]


def test_errors_field():
    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    errors_field = MyMutation._meta.fields['errors']

    assert MyMutation.Errors

    assert type(errors_field.type) == NonNull

    errors_field = errors_field.type.of_type

    assert type(errors_field.text.type) == List
    assert type(errors_field.text.type.of_type) == NonNull
    # TODO: how to test that the nonnull type is a string?
