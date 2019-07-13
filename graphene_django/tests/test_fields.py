import pytest

from graphene import ObjectType, Schema
from graphene.relay import Node
from graphene_django import DjangoConnectionField, DjangoObjectType
from graphene_django.tests.models import Article, Pet, Reporter

pytestmark = pytest.mark.django_db


def test_required_connection_field():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)

    class Query(ObjectType):
        all_reporters = DjangoConnectionField(ReporterType, required=True)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.all()

    Reporter.objects.create(first_name="John", last_name="Doe")

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    expected = {"allReporters": {"edges": [{"node": {"firstName": "John"}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected
