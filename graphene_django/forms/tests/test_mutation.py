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
        fields = '__all__'
    test_camel = forms.IntegerField(required=False)


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

    def test_default_input_meta_fields(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        self.assertEqual(PetMutation._meta.model, Pet)
        self.assertEqual(PetMutation._meta.return_field_name, "pet")
        self.assertIn("name", PetMutation.Input._meta.fields)
        self.assertIn("client_mutation_id", PetMutation.Input._meta.fields)
        self.assertIn("id", PetMutation.Input._meta.fields)

    def test_exclude_fields_input_meta_fields(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm
                exclude_fields = ['id']

        self.assertEqual(PetMutation._meta.model, Pet)
        self.assertEqual(PetMutation._meta.return_field_name, "pet")
        self.assertIn("name", PetMutation.Input._meta.fields)
        self.assertIn("age", PetMutation.Input._meta.fields)
        self.assertIn("client_mutation_id", PetMutation.Input._meta.fields)
        self.assertNotIn("id", PetMutation.Input._meta.fields)

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

        pet = Pet.objects.create(name="Axel", age=10)

        result = PetMutation.mutate_and_get_payload(None, None, id=pet.pk, name="Mia", age=10)

        self.assertEqual(Pet.objects.count(), 1)
        pet.refresh_from_db()
        self.assertEqual(pet.name, "Mia")
        self.assertEqual(result.errors, [])

    def test_model_form_mutation_updates_existing_(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        result = PetMutation.mutate_and_get_payload(None, None, name="Mia", age=10)

        self.assertEqual(Pet.objects.count(), 1)
        pet = Pet.objects.get()
        self.assertEqual(pet.name, "Mia")
        self.assertEqual(pet.age, 10)
        self.assertEqual(result.errors, [])

    def test_model_form_mutation_mutate_invalid_form(self):
        class PetMutation(DjangoModelFormMutation):
            class Meta:
                form_class = PetForm

        result = PetMutation.mutate_and_get_payload(None, None, test_camel='text')

        # A pet was not created
        self.assertEqual(Pet.objects.count(), 0)

        fields_w_error = {e.field: e.messages for e in result.errors}
        self.assertEqual(len(result.errors), 3)
        self.assertIn("testCamel", fields_w_error)
        self.assertEqual(fields_w_error['testCamel'], ["Enter a whole number."])
        self.assertIn("name", fields_w_error)
        self.assertEqual(fields_w_error['name'], ["This field is required."])
        self.assertIn("age", fields_w_error)
        self.assertEqual(fields_w_error['age'], ["This field is required."])


class FormMutationTests(TestCase):
    def test_default_meta_fields(self):
        class MyMutation(DjangoFormMutation):
            class Meta:
                form_class = MyForm
        self.assertNotIn("text", MyMutation._meta.fields)

    def test_mirror_meta_fields(self):
        class MyMutation(DjangoFormMutation):
            class Meta:
                form_class = MyForm
                mirror_input = True

        self.assertIn("text", MyMutation._meta.fields)

    def test_default_input_meta_fields(self):
        class MyMutation(DjangoFormMutation):
            class Meta:
                form_class = MyForm

        self.assertIn("client_mutation_id", MyMutation.Input._meta.fields)
        self.assertIn("text", MyMutation.Input._meta.fields)

    def test_exclude_fields_input_meta_fields(self):
        class MyMutation(DjangoFormMutation):
            class Meta:
                form_class = MyForm
                exclude_fields = ['text']

        self.assertNotIn("text", MyMutation.Input._meta.fields)
        self.assertIn("client_mutation_id", MyMutation.Input._meta.fields)
