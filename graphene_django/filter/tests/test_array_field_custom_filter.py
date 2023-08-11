import pytest

from ...compat import ArrayField, MissingType


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_array_field_len_filter(schema):
    query = """
    query {
        events (tags_Len: 2) {
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
        {"node": {"name": "Musical"}},
        {"node": {"name": "Ballet"}},
    ]

    query = """
    query {
        events (tags_Len: 0) {
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
        {"node": {"name": "Speech"}},
    ]

    query = """
    query {
        events (tags_Len: 10) {
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

    query = """
    query {
        events (tags_Len: "2") {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert len(result.errors) == 1
    assert result.errors[0].message == 'Int cannot represent non-integer value: "2"'

    query = """
    query {
        events (tags_Len: True) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert len(result.errors) == 1
    assert result.errors[0].message == "Int cannot represent non-integer value: True"


@pytest.mark.skipif(ArrayField is MissingType, reason="ArrayField should exist")
def test_array_field_custom_filter(schema):
    query = """
    query {
        events (tags_Len_In: 2) {
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
        {"node": {"name": "Ballet"}},
        {"node": {"name": "Musical"}},
    ]

    query = """
    query {
        events (tags_Len_In: [0, 2]) {
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
        {"node": {"name": "Ballet"}},
        {"node": {"name": "Musical"}},
        {"node": {"name": "Speech"}},
    ]

    query = """
    query {
        events (tags_Len_In: [10]) {
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

    query = """
    query {
        events (tags_Len_In: []) {
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

    query = """
    query {
        events (tags_Len_In: "12") {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert len(result.errors) == 1
    assert result.errors[0].message == 'Int cannot represent non-integer value: "12"'

    query = """
    query {
        events (tags_Len_In: True) {
            edges {
                node {
                    name
                }
            }
        }
    }
    """
    result = schema.execute(query)
    assert len(result.errors) == 1
    assert result.errors[0].message == "Int cannot represent non-integer value: True"
