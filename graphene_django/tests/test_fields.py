import pytest

from graphene import List, NonNull, ObjectType, Schema, String

from ..fields import DjangoListField
from ..types import DjangoObjectType
from .models import Reporter as ReporterModel


@pytest.mark.django_db
class TestDjangoListField:
    def test_only_django_object_types(self):
        class TestType(ObjectType):
            foo = String()

        with pytest.raises(AssertionError):
            list_field = DjangoListField(TestType)

    def test_non_null_type(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        list_field = DjangoListField(NonNull(Reporter))

        assert isinstance(list_field.type, List)
        assert isinstance(list_field.type.of_type, NonNull)
        assert list_field.type.of_type.of_type is Reporter

    def test_get_django_model(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        list_field = DjangoListField(Reporter)
        assert list_field.model is ReporterModel
