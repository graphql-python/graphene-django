from django import forms
from pytest import raises

import graphene
from graphene_django import DjangoObjectType

from ...tests.models import CHOICES, Film, Reporter
from ..types import DjangoFormFieldObjectType, DjangoFormInputObjectType, DjangoFormObjectType, DjangoFormTypeOptions

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
    form_class = ReporterForm
    only_fields = ('pets', 'email')


def test_query_djangoformtype():
    class MyFormType(DjangoFormObjectType):
        form_class = MyForm
        
        only_fields = ('text_field', 'int_field')
        exclude_fields = []

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
                    "type": "String"
                },
                {
                    "name": "int_field",
                    "type": "Int"
                }
            ]
        }
    }
