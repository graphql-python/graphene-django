from django.db import models
from rest_framework import serializers

import graphene
from graphene import Schema
from graphene_django import DjangoObjectType
from graphene_django.rest_framework.mutation import SerializerMutation


class MyFakeChildModel(models.Model):
    name = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)


class MyFakeParentModel(models.Model):
    name = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)
    child1 = models.OneToOneField(
        MyFakeChildModel, related_name="parent1", on_delete=models.CASCADE
    )
    child2 = models.OneToOneField(
        MyFakeChildModel, related_name="parent2", on_delete=models.CASCADE
    )


class ParentType(DjangoObjectType):
    class Meta:
        model = MyFakeParentModel
        interfaces = (graphene.relay.Node,)
        fields = "__all__"


class ChildType(DjangoObjectType):
    class Meta:
        model = MyFakeChildModel
        interfaces = (graphene.relay.Node,)
        fields = "__all__"


class MyModelChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeChildModel
        fields = "__all__"


class MyModelParentSerializer(serializers.ModelSerializer):
    child1 = MyModelChildSerializer()
    child2 = MyModelChildSerializer()

    class Meta:
        model = MyFakeParentModel
        fields = "__all__"


class MyParentModelMutation(SerializerMutation):
    class Meta:
        serializer_class = MyModelParentSerializer


class Mutation(graphene.ObjectType):
    createParentWithChild = MyParentModelMutation.Field()


def test_create_schema():
    schema = Schema(mutation=Mutation, types=[ParentType, ChildType])
    assert schema
