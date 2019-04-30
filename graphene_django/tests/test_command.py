from django.core import management
from mock import patch, mock_open
from six import StringIO


@patch("graphene_django.management.commands.graphql_schema.Command.save_file")
def test_generate_file_on_call_graphql_schema(savefile_mock, settings):
    out = StringIO()
    management.call_command("graphql_schema", schema="", stdout=out)
    assert "Successfully dumped GraphQL schema to schema.json" in out.getvalue()


@patch("json.dump")
def test_files_are_canonical(dump_mock):
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
