# https://github.com/graphql-python/graphene-django/issues/520

import datetime

import graphene
from django import forms
from graphene import Field, ResolveInfo
from graphene.types.inputobjecttype import InputObjectType
from py.test import mark, raises
from rest_framework import serializers

from ...forms.mutation import DjangoFormMutation
from ...rest_framework.models import MyFakeModel
from ...rest_framework.mutation import SerializerMutation
from ...types import DjangoObjectType


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeModel
        fields = "__all__"


class MyForm(forms.Form):
    text = forms.CharField()


def test_can_use_form_and_serializer_mutations():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer

    class MyFormMutation(DjangoFormMutation):
        class Meta:
            form_class = MyForm

    class Mutation(graphene.ObjectType):
        my_mutation = MyMutation.Field()
        my_form_mutation = MyFormMutation.Field()

    graphene.Schema(mutation=Mutation)
