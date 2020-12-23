import pytest

from graphene import ObjectType, Schema
from graphene.relay import Node
from graphene_django import DjangoObjectType
from graphene_django.tests.models import Pet
from graphene_django.utils import DJANGO_FILTER_INSTALLED

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    from graphene_django.filter import DjangoFilterConnectionField
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )


class PetNode(DjangoObjectType):
    class Meta:
        model = Pet
        interfaces = (Node,)
        filter_fields = {
            "name": ["exact", "in"],
            "age": ["exact", "in", "range"],
        }


class Query(ObjectType):
    pets = DjangoFilterConnectionField(PetNode)


def test_string_in_filter():
    """
    Test in filter on a string field.
    """
    Pet.objects.create(name="Brutus", age=12)
    Pet.objects.create(name="Mimi", age=3)
    Pet.objects.create(name="Jojo, the rabbit", age=3)

    schema = Schema(query=Query)

    query = """
    query {
        pets (name_In: ["Brutus", "Jojo, the rabbit"]) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data["pets"]["edges"] == [
        {"node": {"name": "Brutus"}},
        {"node": {"name": "Jojo, the rabbit"}},
    ]


def test_int_in_filter():
    """
    Test in filter on an integer field.
    """
    Pet.objects.create(name="Brutus", age=12)
    Pet.objects.create(name="Mimi", age=3)
    Pet.objects.create(name="Jojo, the rabbit", age=3)

    schema = Schema(query=Query)

    query = """
    query {
        pets (age_In: [3]) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data["pets"]["edges"] == [
        {"node": {"name": "Mimi"}},
        {"node": {"name": "Jojo, the rabbit"}},
    ]

    query = """
    query {
        pets (age_In: [3, 12]) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data["pets"]["edges"] == [
        {"node": {"name": "Brutus"}},
        {"node": {"name": "Mimi"}},
        {"node": {"name": "Jojo, the rabbit"}},
    ]


def test_int_range_filter():
    """
    Test in filter on an integer field.
    """
    Pet.objects.create(name="Brutus", age=12)
    Pet.objects.create(name="Mimi", age=8)
    Pet.objects.create(name="Jojo, the rabbit", age=3)
    Pet.objects.create(name="Picotin", age=5)

    schema = Schema(query=Query)

    query = """
    query {
        pets (age_Range: [4, 9]) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert not result.errors
    assert result.data["pets"]["edges"] == [
        {"node": {"name": "Mimi"}},
        {"node": {"name": "Picotin"}},
    ]
