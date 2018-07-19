from django import forms
from django.test import TestCase
from py.test import raises

from graphene_django.tests.models import Pet, Film, FilmDetails
from ..mutation import DjangoFormMutation, DjangoModelFormMutation


class MyForm(forms.Form):
    text = forms.CharField()


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = ("name",)


def test_needs_form_class():
    with raises(Exception) as exc:

        class MyMutation(DjangoFormMutation):
            pass

    assert exc.value.args[0] == "form_class is required for DjangoFormMutation"


def test_has_output_fields():
    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    assert "errors" in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    assert "text" in MyMutation.Input._meta.fields


class ModelFormMutationTests(TestCase):
    def test_default_meta_fields(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        self.assertEqual(PetMutation._meta.model, Pet)
        self.assertEqual(PetMutation._meta.return_field_name, "pet")
        self.assertIn("pet", PetMutation._meta.fields)

    def test_return_field_name_is_camelcased(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm
                model = FilmDetails

        self.assertEqual(PetMutation._meta.model, FilmDetails)
        self.assertEqual(PetMutation._meta.return_field_name, "filmDetails")

    def test_custom_return_field_name(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm
                model = Film
                return_field_name = "animal"

        self.assertEqual(PetMutation._meta.model, Film)
        self.assertEqual(PetMutation._meta.return_field_name, "animal")
        self.assertIn("animal", PetMutation._meta.fields)

    def test_model_form_mutation_mutate(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        pet = Pet.objects.create(name="Axel")

        result = PetMutation.mutate_and_get_payload(None, None, id=pet.pk, name="Mia")

        self.assertEqual(Pet.objects.count(), 1)
        pet.refresh_from_db()
        self.assertEqual(pet.name, "Mia")
        self.assertEqual(result.errors, [])

    def test_model_form_mutation_updates_existing_(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        result = PetMutation.mutate_and_get_payload(None, None, name="Mia")

        self.assertEqual(Pet.objects.count(), 1)
        pet = Pet.objects.get()
        self.assertEqual(pet.name, "Mia")
        self.assertEqual(result.errors, [])

    def test_model_form_mutation_mutate_invalid_form(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        result = PetMutation.mutate_and_get_payload(None, None)

        # A pet was not created
        self.assertEqual(Pet.objects.count(), 0)

        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].field, "name")
        self.assertEqual(result.errors[0].messages, ["This field is required."])
