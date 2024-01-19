from django import forms
from pytest import raises

import graphene
from graphene_django import DjangoObjectType

from ...tests.models import CHOICES, Film, Reporter
from ..types import DjangoFormFieldObjectType, DjangoFormInputObjectType, DjangoFormObjectType

# Reporter a_choice CHOICES = ((1, "this"), (2, _("that")))
THIS = CHOICES[0][0]
THIS_ON_CLIENT_CONVERTED = "A_1"

# Film genre choices=[("do", "Documentary"), ("ac", "Action"), ("ot", "Other")],
DOCUMENTARY = "do"
DOCUMENTARY_ON_CLIENT_CONVERTED = "DO"


class FilmForm(forms.ModelForm):
    class Meta:
        model = Film
        exclude = ()


class ReporterType(DjangoObjectType):
    class Meta:
        model = Reporter
        fields = "__all__"


class ReporterForm(forms.ModelForm):
    class Meta:
        model = Reporter
        exclude = ("pets", "email", "fans")


class MyForm(forms.Form):
    text_field = forms.CharField()
    int_field = forms.IntegerField()


class ReporterFormType(DjangoFormObjectType):
    class Meta:
        form_class = ReporterForm


def test_needs_form_class():
    with raises(Exception) as exc:
        class MyFormType(DjangoFormObjectType):
            pass

    assert exc.value.args[0] == "form_class is required for DjangoFormObjectType"


def test_type_form_has_fields():
    class ReporterFormType(DjangoFormObjectType):
        class Meta:
            form_class = ReporterForm
            only_fields = ("first_name", "last_name", "a_choice")

    fields = ["first_name", "last_name", "a_choice", "id"]
    assert all(f in ReporterFormType._meta.fields for f in fields)


def test_type_form_has_fields():
    class MyFormFieldType(DjangoFormFieldObjectType):
        class Meta:
            form_class = MyForm

    fields = ["text_field", "int_field", "id"]
    assert all(f in MyFormFieldType._meta.fields for f in fields)


def test_query_djangoformtype():
    class MyFormType(DjangoFormObjectType):
        class Meta:
            form_class = MyForm

    class MockQuery(graphene.ObjectType):
        form = graphene.Field(
            MyFormType
        )

        @staticmethod
        def resolve_form(parent, info):
            return MyFormType()

    schema = graphene.Schema(query=MockQuery)

    result = schema.execute(
        """ 
            query {
                form {
                    fields {
                        name
                        type
                    }
                }
            }
        
        """
    )
    assert result.errors is None
    assert result.data == {
        "form": {
            "fields": [
                {
                    "name": "text_field",
                    "type": "CharField"
                },
                {
                    "name": "int_field",
                    "type": "IntegerField"
                }
            ]
        }
    }
