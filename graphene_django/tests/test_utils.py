from django.utils.translation import gettext_lazy

from ..utils import camelize, get_model_fields
from .models import Film, Reporter


def test_get_model_fields_no_duplication():
    reporter_fields = get_model_fields(Reporter)
    reporter_name_set = set([field[0] for field in reporter_fields])
    assert len(reporter_fields) == len(reporter_name_set)

    film_fields = get_model_fields(Film)
    film_name_set = set([field[0] for field in film_fields])
    assert len(film_fields) == len(film_name_set)


def test_camelize():
    assert camelize({}) == {}
    assert camelize("value_a") == "value_a"
    assert camelize({"value_a": "value_b"}) == {"valueA": "value_b"}
    assert camelize({"value_a": ["value_b"]}) == {"valueA": ["value_b"]}
    assert camelize({"value_a": ["value_b"]}) == {"valueA": ["value_b"]}
    assert camelize({"nested_field": {"value_a": ["error"], "value_b": ["error"]}}) == {
        "nestedField": {"valueA": ["error"], "valueB": ["error"]}
    }
    assert camelize({"value_a": gettext_lazy("value_b")}) == {"valueA": "value_b"}
    assert camelize({"value_a": [gettext_lazy("value_b")]}) == {"valueA": ["value_b"]}
    assert camelize(gettext_lazy("value_a")) == "value_a"
    assert camelize({gettext_lazy("value_a"): gettext_lazy("value_b")}) == {
        "valueA": "value_b"
    }
    assert camelize({0: {"field_a": ["errors"]}}) == {0: {"fieldA": ["errors"]}}
