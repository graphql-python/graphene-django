import datetime

from pytest import raises
from rest_framework import serializers

from graphene import Field, ResolveInfo, String
from graphene.types.inputobjecttype import InputObjectType

from ...types import DjangoObjectType
from ..models import (
    MyFakeModel,
    MyFakeModelWithChoiceField,
    MyFakeModelWithDate,
    MyFakeModelWithPassword,
)
from ..mutation import SerializerMutation


def mock_info():
    return ResolveInfo(
        None,
        None,
        None,
        None,
        path=None,
        schema=None,
        fragments=None,
        root_value=None,
        operation=None,
        variable_values=None,
        context=None,
        is_awaitable=None,
    )


class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyFakeModel
        fields = "__all__"


class MyModelSerializerWithMethod(serializers.ModelSerializer):
    days_since_last_edit = serializers.SerializerMethodField()

    class Meta:
        model = MyFakeModelWithDate
        fields = "__all__"

    def get_days_since_last_edit(self, obj):
        now = datetime.date(2020, 1, 8)
        return (now - obj.last_edited).days


class MyModelMutation(SerializerMutation):
    class Meta:
        serializer_class = MyModelSerializer


class MySerializer(serializers.Serializer):
    text = serializers.CharField()
    model = MyModelSerializer()

    def create(self, validated_data):
        return validated_data


def test_needs_serializer_class():
    with raises(Exception) as exc:

        class MyMutation(SerializerMutation):
            pass

    assert str(exc.value) == "serializer_class is required for the SerializerMutation"


def test_has_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert "text" in MyMutation._meta.fields
    assert "model" in MyMutation._meta.fields
    assert "errors" in MyMutation._meta.fields


def test_has_input_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    assert "text" in MyMutation.Input._meta.fields
    assert "model" in MyMutation.Input._meta.fields


def test_exclude_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer
            exclude_fields = ["created"]

    assert "cool_name" in MyMutation._meta.fields
    assert "created" not in MyMutation._meta.fields
    assert "errors" in MyMutation._meta.fields
    assert "cool_name" in MyMutation.Input._meta.fields
    assert "created" not in MyMutation.Input._meta.fields


def test_model_serializer_optional_fields():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer
            optional_fields = ("cool_name",)

    assert "cool_name" in MyMutation.Input._meta.fields
    assert MyMutation.Input._meta.fields["cool_name"].type == String


def test_write_only_field():
    class WriteOnlyFieldModelSerializer(serializers.ModelSerializer):
        password = serializers.CharField(write_only=True)

        class Meta:
            model = MyFakeModelWithPassword
            fields = ["cool_name", "password"]

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = WriteOnlyFieldModelSerializer

    result = MyMutation.mutate_and_get_payload(
        None, mock_info(), **{"cool_name": "New Narf", "password": "admin"}
    )

    assert hasattr(result, "cool_name")
    assert not hasattr(
        result, "password"
    ), "'password' is write_only field and shouldn't be visible"


def test_write_only_field_using_extra_kwargs():
    class WriteOnlyFieldModelSerializer(serializers.ModelSerializer):
        class Meta:
            model = MyFakeModelWithPassword
            fields = ["cool_name", "password"]
            extra_kwargs = {"password": {"write_only": True}}

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = WriteOnlyFieldModelSerializer

    result = MyMutation.mutate_and_get_payload(
        None, mock_info(), **{"cool_name": "New Narf", "password": "admin"}
    )

    assert hasattr(result, "cool_name")
    assert not hasattr(
        result, "password"
    ), "'password' is write_only field and shouldn't be visible"


def test_read_only_fields():
    class ReadOnlyFieldModelSerializer(serializers.ModelSerializer):
        id = serializers.CharField(read_only=True)
        cool_name = serializers.CharField(read_only=True)

        class Meta:
            model = MyFakeModelWithPassword
            lookup_field = "id"
            fields = ["id", "cool_name", "password"]

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = ReadOnlyFieldModelSerializer

    assert "password" in MyMutation.Input._meta.fields
    assert "id" in MyMutation.Input._meta.fields
    assert (
        "cool_name" not in MyMutation.Input._meta.fields
    ), "'cool_name' is read_only field and shouldn't be on arguments"


def test_hidden_fields():
    class SerializerWithHiddenField(serializers.Serializer):
        cool_name = serializers.CharField()
        user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = SerializerWithHiddenField

    assert "cool_name" in MyMutation.Input._meta.fields
    assert (
        "user" not in MyMutation.Input._meta.fields
    ), "'user' is hidden field and shouldn't be on arguments"


def test_nested_model():
    class MyFakeModelGrapheneType(DjangoObjectType):
        class Meta:
            model = MyFakeModel
            fields = "__all__"

    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    model_field = MyMutation._meta.fields["model"]
    assert isinstance(model_field, Field)
    assert model_field.type == MyFakeModelGrapheneType

    model_input = MyMutation.Input._meta.fields["model"]
    model_input_type = model_input._type.of_type
    assert issubclass(model_input_type, InputObjectType)
    assert "cool_name" in model_input_type._meta.fields
    assert "created" in model_input_type._meta.fields


def test_mutate_and_get_payload_success():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    result = MyMutation.mutate_and_get_payload(
        None, mock_info(), **{"text": "value", "model": {"cool_name": "other_value"}}
    )
    assert result.errors is None


def test_model_add_mutate_and_get_payload_success():
    result = MyModelMutation.mutate_and_get_payload(
        None, mock_info(), **{"cool_name": "Narf"}
    )
    assert result.errors is None
    assert result.cool_name == "Narf"
    assert isinstance(result.created, datetime.datetime)


def test_model_update_mutate_and_get_payload_success():
    instance = MyFakeModel.objects.create(cool_name="Narf")
    result = MyModelMutation.mutate_and_get_payload(
        None, mock_info(), **{"id": instance.id, "cool_name": "New Narf"}
    )
    assert result.errors is None
    assert result.cool_name == "New Narf"


def test_model_partial_update_mutate_and_get_payload_success():
    instance = MyFakeModel.objects.create(cool_name="Narf")
    result = MyModelMutation.mutate_and_get_payload(
        None, mock_info(), **{"id": instance.id}
    )
    assert result.errors is None
    assert result.cool_name == "Narf"


def test_model_invalid_update_mutate_and_get_payload_success():
    class InvalidModelMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializer
            model_operations = ["update"]

    with raises(Exception) as exc:
        InvalidModelMutation.mutate_and_get_payload(
            None, mock_info(), **{"cool_name": "Narf"}
        )

    assert '"id" required' in str(exc.value)


def test_perform_mutate_success():
    class MyMethodMutation(SerializerMutation):
        class Meta:
            serializer_class = MyModelSerializerWithMethod

    result = MyMethodMutation.mutate_and_get_payload(
        None,
        mock_info(),
        **{"cool_name": "Narf", "last_edited": datetime.date(2020, 1, 4)},
    )

    assert result.errors is None
    assert result.cool_name == "Narf"
    assert result.days_since_last_edit == 4


def test_perform_mutate_success_with_enum_choice_field():
    class ListViewChoiceFieldSerializer(serializers.ModelSerializer):
        choice_type = serializers.ChoiceField(
            choices=[(x.name, x.value) for x in MyFakeModelWithChoiceField.ChoiceType],
            required=False,
        )

        class Meta:
            model = MyFakeModelWithChoiceField
            fields = "__all__"

    class SomeCreateSerializerMutation(SerializerMutation):
        class Meta:
            serializer_class = ListViewChoiceFieldSerializer

    choice_type = {
        "choice_type": SomeCreateSerializerMutation.Input.choice_type.type.get("ASDF")
    }
    name = MyFakeModelWithChoiceField.ChoiceType.ASDF.name
    result = SomeCreateSerializerMutation.mutate_and_get_payload(
        None, mock_info(), **choice_type
    )
    assert result.errors is None
    assert result.choice_type == name
    kwargs = SomeCreateSerializerMutation.get_serializer_kwargs(
        None, mock_info(), **choice_type
    )
    assert kwargs["data"]["choice_type"] == name
    assert 1 == MyFakeModelWithChoiceField.objects.count()
    item = MyFakeModelWithChoiceField.objects.first()
    assert item.choice_type == name


def test_mutate_and_get_payload_error():
    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = MySerializer

    # missing required fields
    result = MyMutation.mutate_and_get_payload(None, mock_info(), **{})
    assert len(result.errors) > 0


def test_model_mutate_and_get_payload_error():
    # missing required fields
    result = MyModelMutation.mutate_and_get_payload(None, mock_info(), **{})
    assert len(result.errors) > 0


def test_mutation_error_camelcased(graphene_settings):
    graphene_settings.CAMELCASE_ERRORS = True
    result = MyModelMutation.mutate_and_get_payload(None, mock_info(), **{})
    assert result.errors[0].field == "coolName"


def test_invalid_serializer_operations():
    with raises(Exception) as exc:

        class MyModelMutation(SerializerMutation):
            class Meta:
                serializer_class = MyModelSerializer
                model_operations = ["Add"]

    assert "model_operations" in str(exc.value)
