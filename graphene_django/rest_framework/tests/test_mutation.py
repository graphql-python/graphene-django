from django.db import models
from graphene import Field
from graphene.types.inputobjecttype import InputObjectType
from py.test import raises
from rest_framework import serializers

from ...types import DjangoObjectType
from ..mutation import SerializerMutation


class MyFakeModel(models.Model):
    cool_name = models.CharField(max_length=50)


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeModel
        fields = '__all__'


class MySerializer(serializers.Serializer):
    text = serializers.CharField()
    model = MyModelSerializer()

    def create(self, validated_data):
        return validated_data


def test_needs_serializer_class():
    with raises(Exception) as exc:
        class MyMutation(SerializerMutation):
            pass

    assert str(exc.value) == 'serializer_class is required for the SerializerMutation'


def test_has_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert 'text' in MyMutation._meta.fields
    assert 'model' in MyMutation._meta.fields
    assert 'errors' in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert 'text' in MyMutation.Input._meta.fields
    assert 'model' in MyMutation.Input._meta.fields


def test_nested_model():

    class MyFakeModelGrapheneType(DjangoObjectType):
        class Meta:
            model = MyFakeModel

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    model_field = MyMutation._meta.fields['model']
    assert isinstance(model_field, Field)
    assert model_field.type == MyFakeModelGrapheneType

    model_input = MyMutation.Input._meta.fields['model']
    model_input_type = model_input._type.of_type
    assert issubclass(model_input_type, InputObjectType)
    assert 'cool_name' in model_input_type._meta.fields


def test_mutate_and_get_payload_success():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    result = MyMutation.mutate_and_get_payload(None, None, **{
        'text': 'value',
        'model': {
            'cool_name': 'other_value'
        }
    })
    assert result.errors is None


def test_mutate_and_get_payload_error():

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    # missing required fields
    result = MyMutation.mutate_and_get_payload(None, None, **{})
    assert len(result.errors) > 0