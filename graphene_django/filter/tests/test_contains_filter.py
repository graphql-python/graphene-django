import pytest

from graphene import Schema

from ...compat import ArrayField, MissingType


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_string_contains_multiple(Query):
    """
    Test contains filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Contains: ["concert", "music"]) {
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
    assert result.data["events"]["edges"] == [
        {"node": {"name": "Live Show"}},
    ]


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_string_contains_one(Query):
    """
    Test contains filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Contains: ["music"]) {
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
    assert result.data["events"]["edges"] == [
        {"node": {"name": "Live Show"}},
        {"node": {"name": "Musical"}},
    ]


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_string_contains_none(Query):
    """
    Test contains filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Contains: []) {
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
    assert result.data["events"]["edges"] == []
