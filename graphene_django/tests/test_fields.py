import pytest
from graphene import ObjectType, Schema

from ..fields import DjangoListField
from ..types import DjangoObjectType
from .models import Reporter as ReporterModel


@pytest.mark.django_db
class TestDjangoListField:
    def test_get_django_model(self):
        class Reporter(DjangoObjectType):
            class Meta:
                model = ReporterModel
                fields = ("first_name",)

        list_field = DjangoListField(Reporter)
        assert list_field.model is ReporterModel
