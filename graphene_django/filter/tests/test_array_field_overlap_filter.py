import pytest

from ...compat import ArrayField, MissingType


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_array_field_overlap_multiple(schema):
    """
    Test overlap filter on a array field of string.
    """

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
def test_array_field_overlap_one(schema):
    """
    Test overlap filter on a array field of string.
    """

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
def test_array_field_overlap_empty_list(schema):
    """
    Test overlap filter on a array field of string.
    """

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
