import json
import pytest

from django_filters import FilterSet
from django_filters import rest_framework as filters
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
        fields = "__all__"
        filter_fields = {
            "name": ["exact", "in"],
            "age": ["exact", "in", "range"],
        }


class Query(ObjectType):
    pets = DjangoFilterConnectionField(PetNode)


def test_int_range_filter():
    """
    Test range filter on an integer field.
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


def test_range_filter_with_invalid_input():
    """
    Test range filter used with invalid inputs raise an error.
    """
    Pet.objects.create(name="Brutus", age=12)
    Pet.objects.create(name="Mimi", age=8)
    Pet.objects.create(name="Jojo, the rabbit", age=3)
    Pet.objects.create(name="Picotin", age=5)

    schema = Schema(query=Query)

    query = """
    query ($rangeValue: [Int]) {
        pets (age_Range: $rangeValue) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    expected_error = json.dumps(
        {
            "age__range": [
                {
                    "message": "Invalid range specified: it needs to contain 2 values.",
                    "code": "invalid",
                }
            ]
        }
    )

    # Empty list
    result = schema.execute(query, variables={"rangeValue": []})
    assert len(result.errors) == 1
    assert result.errors[0].message == expected_error

    # Only one item in the list
    result = schema.execute(query, variables={"rangeValue": [1]})
    assert len(result.errors) == 1
    assert result.errors[0].message == expected_error

    # More than 2 items in the list
    result = schema.execute(query, variables={"rangeValue": [1, 2, 3]})
    assert len(result.errors) == 1
    assert result.errors[0].message == expected_error
