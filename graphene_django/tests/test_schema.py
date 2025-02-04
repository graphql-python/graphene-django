from pytest import raises

from ..registry import Registry
from ..types import DjangoObjectType
from .models import Reporter


def test_should_raise_if_no_model():
    with raises(Exception) as excinfo:

        class Character1(DjangoObjectType):
            fields = "__all__"

    assert "valid Django Model" in str(excinfo.value)


def test_should_raise_if_model_is_invalid():
    with raises(Exception) as excinfo:

        class Character2(DjangoObjectType):
            class Meta:
                model = 1
                fields = "__all__"

    assert "valid Django Model" in str(excinfo.value)


def test_should_map_fields_correctly():
    class ReporterType2(DjangoObjectType):
        class Meta:
            model = Reporter
            registry = Registry()
            fields = "__all__"

    fields = list(ReporterType2._meta.fields.keys())
    assert fields[:-3] == [
        "id",
        "first_name",
        "last_name",
        "email",
        "pets",
        "a_choice",
        "typed_choice",
        "class_choice",
        "callable_choice",
        "fans",
        "reporter_type",
    ]

    assert sorted(fields[-3:]) == ["apnewsreporter", "articles", "films"]


def test_should_map_only_few_fields():
    class Reporter2(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = ("id", "email")

    assert list(Reporter2._meta.fields.keys()) == ["id", "email"]
