import pytest

from graphene import Schema

from ...compat import ArrayField, MissingType


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_string_overlap_multiple(Event, Query):
    """
    Test overlap filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Overlap: ["concert", "music"]) {
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
        {"node": {"name": "Ballet"}},
    ]


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_string_overlap_one(Event, Query):
    """
    Test overlap filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Overlap: ["music"]) {
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
def test_string_overlap_none(Event, Query):
    """
    Test overlap filter on a string field.
    """

    schema = Schema(query=Query)

    query = """
    query {
        events (tags_Overlap: []) {
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
