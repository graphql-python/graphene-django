from django.db import models

from graphene import Field, Schema, String, Mutation, ObjectType, AbstractType
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
    

def test_custom_serializer(capfd):

    class MyBasicSerializer(serializers.Serializer):
        whatever = serializers.CharField(required=False)
        
        def create(self, data):
            return {'user': self.context['request']['user']}

    class MyBasicGrapheneType(ObjectType):
        text = String()
    
    class MyAwesomeMutation(SerializerMutation):
        
        class Meta:
            serializer_class = MyBasicSerializer
        
        user = String()
        
        @classmethod
        def get_serializer(cls, instance, args, request, info):
            input = args.get('input')
            
            return cls._meta.serializer_class(data=dict(input),
                                              context={'request': request})
                                              
    class MyAbstractMutation(AbstractType, ObjectType):
        myAwesomeMutation = MyAwesomeMutation.Field()
            
    schema = Schema(query=MyBasicGrapheneType, mutation=MyAbstractMutation)    
    mutation = '''
        mutation MutationTest($input: MyBasicSerializerInput!) {
            myAwesomeMutation(input: $input) {
                user
            }
        }
    '''
    
    result = schema.execute(mutation, variable_values={'input': {}},
                            context_value={'user': 1})
    assert result.data['myAwesomeMutation']['user'] == '1'
            
    
