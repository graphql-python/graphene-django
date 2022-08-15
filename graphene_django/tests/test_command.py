from textwrap import dedent

from django.core import management
from io import StringIO
from mock import mock_open, patch

from graphene import ObjectType, Schema, String


@patch("graphene_django.management.commands.graphql_schema.Command.save_json_file")
def test_generate_json_file_on_call_graphql_schema(savefile_mock):
    out = StringIO()
    management.call_command("graphql_schema", schema="", stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()


@patch("json.dump")
def test_json_files_are_canonical(dump_mock):
    open_mock = mock_open()
    with patch("graphene_django.management.commands.graphql_schema.open", open_mock):
        management.call_command("graphql_schema", schema="")

    open_mock.assert_called_once()

    dump_mock.assert_called_once()
    assert dump_mock.call_args[1][
        "sort_keys"
    ], "json.mock() should be used to sort the output"
    assert (
        dump_mock.call_args[1]["indent"] > 0
    ), "output should be pretty-printed by default"


def test_generate_graphql_file_on_call_graphql_schema():
    class Query(ObjectType):
        hi = String()

    mock_schema = Schema(query=Query)

    open_mock = mock_open()
    with patch("graphene_django.management.commands.graphql_schema.open", open_mock):
        management.call_command(
            "graphql_schema", schema=mock_schema, out="schema.graphql"
        )

    open_mock.assert_called_once()

    handle = open_mock()
    assert handle.write.called_once()

    schema_output = handle.write.call_args[0][0]
    assert schema_output == dedent(
        """\
        type Query {
          hi: String
        }"""
    )
