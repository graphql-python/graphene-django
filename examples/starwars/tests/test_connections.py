import pytest

from ..data import initialize
from ..schema import schema

pytestmark = pytest.mark.django_db


def test_correct_fetch_first_ship_rebels():
    initialize()
    query = """
    query RebelsShipsQuery {
      rebels {
        name,
        hero {
          name
        }
        ships(first: 1) {
          edges {
            node {
              name
            }
          }
        }
      }
    }
    """
    expected = {
        "rebels": {
            "name": "Alliance to Restore the Republic",
            "hero": {"name": "Human"},
            "ships": {"edges": [{"node": {"name": "X-Wing"}}]},
        }
    }
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_correct_list_characters():
    initialize()
    query = """
    query RebelsShipsQuery {
      node(id: "U2hpcDox") {
        ... on Ship {
          name
          characters {
            name
          }
        }
      }
    }
    """
    expected = {"node": {"name": "X-Wing", "characters": [{"name": "Human"}]}}
    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected
