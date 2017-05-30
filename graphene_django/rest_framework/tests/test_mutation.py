from py.test import raises
from rest_framework import serializers

from ..mutation import SerializerMutation


class MySerializer(serializers.Serializer):
    text = serializers.CharField()


def test_needs_serializer_class():
    with raises(Exception) as exc:
        class MyMutation(SerializerMutation):
            pass

    assert exc.value.args[0] == 'Missing serializer_class'


def test_has_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert 'text' in MyMutation._meta.fields
    assert 'errors' in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert 'text' in MyMutation.Input._meta.fields


