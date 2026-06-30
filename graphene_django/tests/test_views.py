import json
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.db import connection

from .models import Pet

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


def url_string(string="/graphql", **url_params):
    if url_params:
        string += "?" + urlencode(url_params)

    return string


def batch_url_string(**url_params):
    return url_string("/graphql/batch", **url_params)


def response_json(response):
    return json.loads(response.content.decode())


def j(**kwargs):
    return json.dumps(kwargs)


def jl(**kwargs):
    return json.dumps([kwargs])


def test_graphiql_is_enabled(client):
    response = client.get(url_string(), HTTP_ACCEPT="text/html")
    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"].split(";")[0] == "text/html"


def test_qfactor_graphiql(client):
    response = client.get(
        url_string(query="{test}"),
        HTTP_ACCEPT="application/json;q=0.8, text/html;q=0.9",
    )
    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"].split(";")[0] == "text/html"


def test_qfactor_json(client):
    response = client.get(
        url_string(query="{test}"),
        HTTP_ACCEPT="text/html;q=0.8, application/json;q=0.9",
    )
    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"].split(";")[0] == "application/json"
    assert response_json(response) == {"data": {"test": "Hello World"}}


def test_allows_get_with_query_param(client):
    response = client.get(url_string(query="{test}"))

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello World"}}


def test_allows_get_with_variable_values(client):
    response = client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        )
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_allows_get_with_operation_name(client):
    response = client.get(
        url_string(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        )
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


def test_reports_validation_errors(client):
    response = client.get(url_string(query="{ test, unknownOne, unknownTwo }"))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [
            {
                "message": "Cannot query field 'unknownOne' on type 'QueryRoot'.",
                "locations": [{"line": 1, "column": 9}],
            },
            {
                "message": "Cannot query field 'unknownTwo' on type 'QueryRoot'.",
                "locations": [{"line": 1, "column": 21}],
            },
        ]
    }


def test_errors_when_missing_operation_name(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """
        )
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [
            {
                "message": "Must provide operation name if query contains multiple operations.",
            }
        ]
    }


def test_errors_when_sending_a_mutation_via_get(client):
    response = client.get(
        url_string(
            query="""
        mutation TestMutation { writeTest { test } }
        """
        )
    )
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response_json(response) == {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }


def test_errors_when_selecting_a_mutation_within_a_get(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestMutation",
        )
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response_json(response) == {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }


def test_allows_mutation_to_exist_within_a_get(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """,
            operationName="TestQuery",
        )
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello World"}}


def test_allows_post_with_json_encoding(client):
    response = client.post(url_string(), j(query="{test}"), "application/json")

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello World"}}


def test_batch_allows_post_with_json_encoding(client):
    response = client.post(
        batch_url_string(), jl(id=1, query="{test}"), "application/json"
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == [
        {"id": 1, "data": {"test": "Hello World"}, "status": 200}
    ]


def test_batch_fails_if_is_empty(client):
    response = client.post(batch_url_string(), "[]", "application/json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "Received an empty list in the batch request."}]
    }


def test_allows_sending_a_mutation_via_post(client):
    response = client.post(
        url_string(),
        j(query="mutation TestMutation { writeTest { test } }"),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"writeTest": {"test": "Hello World"}}}


def test_allows_post_with_url_encoding(client):
    response = client.post(
        url_string(),
        urlencode({"query": "{test}"}),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello World"}}


def test_supports_post_json_query_with_string_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_batch_supports_post_json_query_with_string_variables(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == [
        {"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}
    ]


def test_supports_post_json_query_with_json_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_batch_supports_post_json_query_with_json_variables(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == [
        {"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}
    ]


def test_supports_post_url_encoded_query_with_string_variables(client):
    response = client.post(
        url_string(),
        urlencode(
            {
                "query": "query helloWho($who: String){ test(who: $who) }",
                "variables": json.dumps({"who": "Dolly"}),
            }
        ),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_supports_post_json_quey_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        j(query="query helloWho($who: String){ test(who: $who) }"),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_post_url_encoded_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        urlencode({"query": "query helloWho($who: String){ test(who: $who) }"}),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_supports_post_raw_text_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        "application/graphql",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"test": "Hello Dolly"}}


def test_allows_post_with_operation_name(client):
    response = client.post(
        url_string(),
        j(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


def test_batch_allows_post_with_operation_name(client):
    response = client.post(
        batch_url_string(),
        jl(
            id=1,
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
        "application/json",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == [
        {
            "id": 1,
            "data": {"test": "Hello World", "shared": "Hello Everyone"},
            "status": 200,
        }
    ]


def test_allows_post_with_get_operation_name(client):
    response = client.post(
        url_string(operationName="helloWorld"),
        """
    query helloYou { test(who: "You"), ...shared }
    query helloWorld { test(who: "World"), ...shared }
    query helloDolly { test(who: "Dolly"), ...shared }
    fragment shared on QueryRoot {
      shared: test(who: "Everyone")
    }
    """,
        "application/graphql",
    )

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {
        "data": {"test": "Hello World", "shared": "Hello Everyone"}
    }


@pytest.mark.urls("graphene_django.tests.urls_inherited")
def test_inherited_class_with_attributes_works(client):
    inherited_url = "/graphql/inherited/"
    # Check schema and pretty attributes work
    response = client.post(url_string(inherited_url, query="{test}"))
    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )

    # Check graphiql works
    response = client.get(url_string(inherited_url), HTTP_ACCEPT="text/html")
    assert response.status_code == HTTPStatus.OK


@pytest.mark.urls("graphene_django.tests.urls_pretty")
def test_supports_pretty_printing(client):
    response = client.get(url_string(query="{test}"))

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


def test_supports_pretty_printing_by_request(client):
    response = client.get(url_string(query="{test}", pretty="1"))

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


def test_handles_field_errors_caught_by_graphql(client):
    response = client.get(url_string(query="{thrower}"))
    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {
        "data": None,
        "errors": [
            {
                "locations": [{"column": 2, "line": 1}],
                "path": ["thrower"],
                "message": "Throws!",
            }
        ],
    }


def test_handles_syntax_errors_caught_by_graphql(client):
    response = client.get(url_string(query="syntaxerror"))
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [
            {
                "locations": [{"column": 1, "line": 1}],
                "message": "Syntax Error: Unexpected Name 'syntaxerror'.",
            }
        ]
    }


def test_handles_errors_caused_by_a_lack_of_query(client):
    response = client.get(url_string())

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "Must provide query string."}]
    }


def test_handles_not_expected_json_bodies(client):
    response = client.post(url_string(), "[]", "application/json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "The received data is not a valid JSON query."}]
    }


def test_handles_invalid_json_bodies(client):
    response = client.post(url_string(), "[oh}", "application/json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "POST body sent invalid JSON."}]
    }


def test_handles_django_request_error(client, monkeypatch):
    def mocked_read(*args):
        raise OSError("foo-bar")

    monkeypatch.setattr("django.http.request.HttpRequest.read", mocked_read)

    valid_json = json.dumps({"foo": "bar"})
    response = client.post(url_string(), valid_json, "application/json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {"errors": [{"message": "foo-bar"}]}


def test_handles_incomplete_json_bodies(client):
    response = client.post(url_string(), '{"query":', "application/json")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "POST body sent invalid JSON."}]
    }


def test_handles_plain_post_text(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        "text/plain",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "Must provide query string."}]
    }


def test_handles_poorly_formed_variables(client):
    response = client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }", variables="who:You"
        )
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response_json(response) == {
        "errors": [{"message": "Variables are invalid JSON."}]
    }


def test_handles_unsupported_http_methods(client):
    response = client.put(url_string(query="{test}"))
    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert response["Allow"] == "GET, POST"
    assert response_json(response) == {
        "errors": [{"message": "GraphQL only supports GET and POST requests."}]
    }


def test_passes_request_into_context_request(client):
    response = client.get(url_string(query="{request}", q="testing"))

    assert response.status_code == HTTPStatus.OK
    assert response_json(response) == {"data": {"request": "testing"}}


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": True}
)
def test_form_mutation_multiple_creation_invalid_atomic_request(client):
    query = """
    mutation PetMutations {
        petFormMutation1: petFormMutation(input: { name: "Mia", age: 99 }) {
            errors {
                field
                messages
            }
        }
        petFormMutation2: petFormMutation(input: { name: "Enzo", age: 0 }) {
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petFormMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petFormMutation2"]["errors"] == []

    assert Pet.objects.count() == 0


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": True, "ATOMIC_REQUESTS": False}
)
def test_form_mutation_multiple_creation_invalid_atomic_mutation_1(client):
    query = """
    mutation PetMutations {
        petFormMutation1: petFormMutation(input: { name: "Mia", age: 99 }) {
            errors {
                field
                messages
            }
        }
        petFormMutation2: petFormMutation(input: { name: "Enzo", age: 0 }) {
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petFormMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petFormMutation2"]["errors"] == []

    assert Pet.objects.count() == 0


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", True)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": False}
)
def test_form_mutation_multiple_creation_invalid_atomic_mutation_2(client):
    query = """
    mutation PetMutations {
        petFormMutation1: petFormMutation(input: { name: "Mia", age: 99 }) {
            errors {
                field
                messages
            }
        }
        petFormMutation2: petFormMutation(input: { name: "Enzo", age: 0 }) {
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petFormMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petFormMutation2"]["errors"] == []

    assert Pet.objects.count() == 0


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": False}
)
def test_form_mutation_multiple_creation_invalid_non_atomic(client):
    query = """
    mutation PetMutations {
        petFormMutation1: petFormMutation(input: { name: "Mia", age: 99 }) {
            errors {
                field
                messages
            }
        }
        petFormMutation2: petFormMutation(input: { name: "Enzo", age: 0 }) {
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petFormMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petFormMutation2"]["errors"] == []

    assert Pet.objects.count() == 1

    pet = Pet.objects.get()
    assert pet.name == "Enzo"
    assert pet.age == 0


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": True}
)
def test_model_form_mutation_multiple_creation_invalid_atomic_request(client):
    query = """
    mutation PetMutations {
        petMutation1: petMutation(input: { name: "Mia", age: 99 }) {
            pet {
                name
                age
            }
            errors {
                field
                messages
            }
        }
        petMutation2: petMutation(input: { name: "Enzo", age: 0 }) {
            pet {
                name
                age
            }
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petMutation1"]["pet"] is None
    assert content["data"]["petMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petMutation2"]["pet"] == {"name": "Enzo", "age": 0}

    assert Pet.objects.count() == 0


@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": False}
)
def test_model_form_mutation_multiple_creation_invalid_non_atomic(client):
    query = """
    mutation PetMutations {
        petMutation1: petMutation(input: { name: "Mia", age: 99 }) {
            pet {
                name
                age
            }
            errors {
                field
                messages
            }
        }
        petMutation2: petMutation(input: { name: "Enzo", age: 0 }) {
            pet {
                name
                age
            }
            errors {
                field
                messages
            }
        }
    }
    """

    response = client.post(url_string(query=query))
    content = response_json(response)

    assert "errors" not in content

    assert content["data"]["petMutation1"]["pet"] is None
    assert content["data"]["petMutation1"]["errors"] == [
        {"field": "age", "messages": ["Too old"]}
    ]

    assert content["data"]["petMutation2"]["pet"] == {"name": "Enzo", "age": 0}

    assert Pet.objects.count() == 1

    pet = Pet.objects.get()
    assert pet.name == "Enzo"
    assert pet.age == 0


@patch("graphene_django.utils.utils.transaction.set_rollback")
@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": True}
)
def test_query_errors_atomic_request(set_rollback_mock, client):
    client.get(url_string(query="force error"))
    set_rollback_mock.assert_called_once_with(True)


@patch("graphene_django.utils.utils.transaction.set_rollback")
@patch("graphene_django.settings.graphene_settings.ATOMIC_MUTATIONS", False)
@patch.dict(
    connection.settings_dict, {"ATOMIC_MUTATIONS": False, "ATOMIC_REQUESTS": False}
)
def test_query_errors_non_atomic(set_rollback_mock, client):
    client.get(url_string(query="force error"))
    set_rollback_mock.assert_not_called()


VALIDATION_URLS = [
    "/graphql/validation/",
    "/graphql/validation/alternative/",
    "/graphql/validation/inherited/",
]

QUERY_WITH_TWO_INTROSPECTIONS = """
query Instrospection {
    queryType: __schema {
        queryType {name}
    }
    mutationType: __schema {
        mutationType {name}
    }
}
"""

N_INTROSPECTIONS = 2

INTROSPECTION_DISALLOWED_ERROR_MESSAGE = "introspection is disabled"
MAX_VALIDATION_ERRORS_EXCEEDED_MESSAGE = "too many validation errors"


@pytest.mark.urls("graphene_django.tests.urls_validation")
def test_allow_introspection(client):
    response = client.post(
        url_string("/graphql/", query="{__schema {queryType {name}}}")
    )
    assert response.status_code == HTTPStatus.OK

    assert response_json(response) == {
        "data": {"__schema": {"queryType": {"name": "QueryRoot"}}}
    }


@pytest.mark.parametrize("url", VALIDATION_URLS)
@pytest.mark.urls("graphene_django.tests.urls_validation")
def test_validation_disallow_introspection(client, url):
    response = client.post(url_string(url, query="{__schema {queryType {name}}}"))

    assert response.status_code == HTTPStatus.BAD_REQUEST

    json_response = response_json(response)
    assert "data" not in json_response
    assert "errors" in json_response
    assert len(json_response["errors"]) == 1

    error_message = json_response["errors"][0]["message"]
    assert INTROSPECTION_DISALLOWED_ERROR_MESSAGE in error_message


@pytest.mark.parametrize("url", VALIDATION_URLS)
@pytest.mark.urls("graphene_django.tests.urls_validation")
@patch(
    "graphene_django.settings.graphene_settings.MAX_VALIDATION_ERRORS", N_INTROSPECTIONS
)
def test_within_max_validation_errors(client, url):
    response = client.post(url_string(url, query=QUERY_WITH_TWO_INTROSPECTIONS))

    assert response.status_code == HTTPStatus.BAD_REQUEST

    json_response = response_json(response)
    assert "data" not in json_response
    assert "errors" in json_response
    assert len(json_response["errors"]) == N_INTROSPECTIONS

    error_messages = [error["message"].lower() for error in json_response["errors"]]

    n_introspection_error_messages = sum(
        INTROSPECTION_DISALLOWED_ERROR_MESSAGE in msg for msg in error_messages
    )
    assert n_introspection_error_messages == N_INTROSPECTIONS

    assert all(
        MAX_VALIDATION_ERRORS_EXCEEDED_MESSAGE not in msg for msg in error_messages
    )


@pytest.mark.parametrize("url", VALIDATION_URLS)
@pytest.mark.urls("graphene_django.tests.urls_validation")
@patch("graphene_django.settings.graphene_settings.MAX_VALIDATION_ERRORS", 1)
def test_exceeds_max_validation_errors(client, url):
    response = client.post(url_string(url, query=QUERY_WITH_TWO_INTROSPECTIONS))

    assert response.status_code == HTTPStatus.BAD_REQUEST

    json_response = response_json(response)
    assert "data" not in json_response
    assert "errors" in json_response

    error_messages = (error["message"].lower() for error in json_response["errors"])
    assert any(MAX_VALIDATION_ERRORS_EXCEEDED_MESSAGE in msg for msg in error_messages)


class TestExecuteGraphqlRequestRefactor:
    """Pin the ``execute_graphql_request`` extraction in
    :mod:`graphene_django.views`.

    The refactor introduced two private helpers,
    :meth:`GraphQLView._should_short_circuit_get_request` and
    :meth:`GraphQLView._is_atomic_mutation`, and the tests in this class
    exercise the previously-implicit branches that those helpers now
    cover so that any regression fails a focused test.

    Scenarios covered:

    * ``_should_short_circuit_get_request``
        - POST never short-circuits regardless of operation kind.
        - GET + query never short-circuits (the B1 regression: an earlier
          rewrite of this branch caused queries with ``show_graphiql=True``
          to be silently dropped).
        - GET + non-query + ``show_graphiql=True`` short-circuits to
          ``True`` so the caller returns ``None``.
        - GET + non-query + ``show_graphiql=False`` raises ``HttpError``
          carrying a 405 ``HttpResponseNotAllowed``.
        - GET with ``operation_ast=None`` (e.g. an unparseable document)
          does not short-circuit; the executor sees the error.
    * ``_is_atomic_mutation``
        - Parametrised over the 8 combinations of (operation kind,
          ATOMIC_MUTATIONS setting, db ATOMIC_MUTATIONS setting),
          asserting the boolean outcome for each.
    * ``execute_graphql_request`` end-to-end
        - GET + query + ``show_graphiql=True`` invoked directly returns
          a non-None ``ExecutionResult`` with the query's data (B1 pin).
        - GET + mutation + ``show_graphiql=True`` invoked directly
          returns ``None`` (existing behaviour preserved).
        - ``get_operation_ast`` is invoked exactly once per request (B2
          pin: the original PR introduced a second call).
    * ``GraphQLView.__init__``
        - Constructing the view with ``graphene_settings.MIDDLEWARE = None``
          succeeds and yields ``view.middleware is None`` (B3 pin: the
          original PR dropped the ``if middleware is not None`` guard,
          which would have raised ``TypeError``).

    Assumptions: the existing :data:`graphene_django.tests.schema_view.schema`
    exposes a ``test`` query and a ``writeTest`` mutation, both used as
    minimal exercises of the query and mutation branches respectively.
    """

    @staticmethod
    def _make_view():
        """Build a :class:`GraphQLView` against the existing test schema."""
        from graphene_django.views import GraphQLView

        from .schema_view import schema

        return GraphQLView(schema=schema)

    @staticmethod
    def _build_request(method, **get_params):
        """Build a tiny stand-in for a Django HttpRequest.

        ``execute_graphql_request`` only reads ``request.method`` (in the
        ``_should_short_circuit_get_request`` helper) and is otherwise
        agnostic to the request object, so a SimpleNamespace is enough
        for these unit tests and avoids spinning up the full request
        factory.
        """
        from types import SimpleNamespace

        return SimpleNamespace(method=method, GET={}, META={})

    def test_should_short_circuit_returns_false_for_post(self):
        """
        Name: short-circuit, POST is never short-circuited
        Description: ``_should_short_circuit_get_request`` must return
            ``False`` for POST requests so all operation kinds (queries,
            mutations, subscriptions) are routed to the executor.
        Assumptions: A POST mutation is the canonical "do not
            short-circuit" case.
        Expectations: Returns ``False``.
        """
        from graphql import OperationType, parse, get_operation_ast

        from graphene_django.views import GraphQLView

        document = parse("mutation { writeTest { test } }")
        op_ast = get_operation_ast(document, None)
        assert op_ast.operation == OperationType.MUTATION

        request = self._build_request("post")
        assert (
            GraphQLView._should_short_circuit_get_request(request, op_ast, True)
            is False
        )

    def test_should_short_circuit_returns_false_for_get_query(self):
        """
        Name: short-circuit, GET + query never short-circuits (B1 pin)
        Description: A query operation on a GET request must always be
            executed normally, even when GraphiQL is rendering. This is
            the regression the PR refactor introduced and that the
            ``_should_short_circuit_get_request`` helper is designed to
            prevent.
        Assumptions: ``test`` is a query in :data:`schema_view.schema`.
        Expectations: Returns ``False`` regardless of ``show_graphiql``.
        """
        from graphql import OperationType, parse, get_operation_ast

        from graphene_django.views import GraphQLView

        document = parse("{ test }")
        op_ast = get_operation_ast(document, None)
        assert op_ast.operation == OperationType.QUERY

        request = self._build_request("get")
        assert (
            GraphQLView._should_short_circuit_get_request(request, op_ast, True)
            is False
        )
        assert (
            GraphQLView._should_short_circuit_get_request(request, op_ast, False)
            is False
        )

    def test_should_short_circuit_returns_true_for_get_mutation_with_graphiql(self):
        """
        Name: short-circuit, GET + mutation + show_graphiql=True
        Description: The only case that short-circuits to ``True`` is a
            non-query operation on a GET request when GraphiQL is
            rendering, so the caller can return ``None`` without raising.
        Assumptions: ``writeTest`` is a mutation in
            :data:`schema_view.schema`.
        Expectations: Returns ``True``.
        """
        from graphql import OperationType, parse, get_operation_ast

        from graphene_django.views import GraphQLView

        document = parse("mutation { writeTest { test } }")
        op_ast = get_operation_ast(document, None)
        assert op_ast.operation == OperationType.MUTATION

        request = self._build_request("get")
        assert (
            GraphQLView._should_short_circuit_get_request(request, op_ast, True)
            is True
        )

    def test_should_short_circuit_raises_for_get_mutation_without_graphiql(self):
        """
        Name: short-circuit, GET + mutation + no GraphiQL raises 405
        Description: A non-query GET request without GraphiQL must raise
            ``HttpError`` carrying a 405 ``HttpResponseNotAllowed`` so the
            client gets the documented "Can only perform a {} operation
            from a POST request" error.
        Assumptions: The operation is a mutation.
        Expectations: ``HttpError`` is raised; the wrapped response is a
            405 with the expected message.
        """
        from http import HTTPStatus

        from graphql import OperationType, parse, get_operation_ast

        from graphene_django.views import GraphQLView, HttpError

        document = parse("mutation { writeTest { test } }")
        op_ast = get_operation_ast(document, None)
        assert op_ast.operation == OperationType.MUTATION

        request = self._build_request("get")
        with pytest.raises(HttpError) as excinfo:
            GraphQLView._should_short_circuit_get_request(request, op_ast, False)
        assert excinfo.value.response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
        assert (
            "Can only perform a mutation operation from a POST request."
            in excinfo.value.message
        )

    def test_should_short_circuit_returns_false_when_operation_ast_is_none(self):
        """
        Name: short-circuit, missing operation_ast
        Description: When ``get_operation_ast`` couldn't resolve an
            operation (e.g. operation_name not found on the document), the
            helper must not short-circuit; downstream validation will
            surface the appropriate error to the user.
        Assumptions: ``operation_ast`` is allowed to be ``None``.
        Expectations: Returns ``False`` for both GET and POST.
        """
        from graphene_django.views import GraphQLView

        for method in ("get", "post"):
            request = self._build_request(method)
            assert (
                GraphQLView._should_short_circuit_get_request(request, None, True)
                is False
            )
            assert (
                GraphQLView._should_short_circuit_get_request(request, None, False)
                is False
            )

    @pytest.mark.parametrize(
        "operation_str,atomic_global,atomic_db,expected",
        [
            # Queries are never atomic regardless of settings.
            ("{ test }", True, True, False),
            ("{ test }", False, False, False),
            # Mutations require at least one of the two flags.
            ("mutation { writeTest { test } }", False, False, False),
            ("mutation { writeTest { test } }", True, False, True),
            ("mutation { writeTest { test } }", False, True, True),
            ("mutation { writeTest { test } }", True, True, True),
        ],
    )
    def test_is_atomic_mutation_combinations(
        self, monkeypatch, operation_str, atomic_global, atomic_db, expected
    ):
        """
        Name: _is_atomic_mutation, parametrised settings
        Description: ``_is_atomic_mutation`` must return ``True`` only when
            the operation is a mutation **and** at least one of the two
            ATOMIC_MUTATIONS flags (graphene setting or per-connection db
            setting) is enabled.
        Assumptions: The two-flag rule mirrors the original inline logic
            in ``execute_graphql_request``.
        Expectations: For each ``(operation_kind, atomic_global, atomic_db)``
            combination, the helper returns the documented boolean.
        """
        from django.db import connection as db_connection
        from graphql import parse, get_operation_ast

        from graphene_django.views import GraphQLView

        monkeypatch.setattr(
            "graphene_django.views.graphene_settings.ATOMIC_MUTATIONS",
            atomic_global,
        )
        monkeypatch.setitem(
            db_connection.settings_dict, "ATOMIC_MUTATIONS", atomic_db
        )

        document = parse(operation_str)
        op_ast = get_operation_ast(document, None)
        assert GraphQLView._is_atomic_mutation(op_ast) is expected

    def test_is_atomic_mutation_returns_false_for_none_operation(self):
        """
        Name: _is_atomic_mutation, missing operation_ast
        Description: With no operation AST, the helper must return ``False``
            so the caller does not wrap an unparseable document in a
            transaction.
        Assumptions: ``operation_ast`` is allowed to be ``None``.
        Expectations: Returns ``False``.
        """
        from graphene_django.views import GraphQLView

        assert GraphQLView._is_atomic_mutation(None) is False

    def test_execute_graphql_request_get_with_query_and_graphiql_executes(self):
        """
        Name: execute_graphql_request, GET + query + show_graphiql=True (B1 pin)
        Description: Calling ``execute_graphql_request`` directly with
            ``show_graphiql=True`` and a query must still execute the
            query and return a non-None ``ExecutionResult``. The earlier
            rewrite of this code path returned ``None`` unconditionally
            on ``show_graphiql=True``, dropping the result silently.
        Assumptions: ``test`` is a String query on :data:`schema_view.schema`
            that returns ``"Hello World"`` when called without arguments.
        Expectations: The returned ``ExecutionResult`` has no errors and
            ``result.data == {"test": "Hello World"}``.
        """
        view = self._make_view()
        request = self._build_request("get")

        result = view.execute_graphql_request(
            request,
            data={},
            query="{ test }",
            variables=None,
            operation_name=None,
            show_graphiql=True,
        )
        assert result is not None
        assert result.errors is None
        assert result.data == {"test": "Hello World"}

    def test_execute_graphql_request_get_with_mutation_and_graphiql_returns_none(
        self,
    ):
        """
        Name: execute_graphql_request, GET + mutation + show_graphiql=True
        Description: A non-query operation on a GET request with GraphiQL
            rendering must short-circuit to ``None`` so GraphiQL can be
            displayed without executing the mutation. This mirrors the
            existing public behaviour and protects it across the
            extraction.
        Assumptions: ``writeTest`` is a mutation on :data:`schema_view.schema`.
        Expectations: Returns ``None``.
        """
        view = self._make_view()
        request = self._build_request("get")

        result = view.execute_graphql_request(
            request,
            data={},
            query="mutation { writeTest { test } }",
            variables=None,
            operation_name=None,
            show_graphiql=True,
        )
        assert result is None

    def test_execute_graphql_request_calls_get_operation_ast_once(self, monkeypatch):
        """
        Name: execute_graphql_request, single get_operation_ast call (B2 pin)
        Description: The refactor must continue to call ``get_operation_ast``
            exactly once per request — the original PR introduced a second
            call inside the extracted validation helper, which this test
            prevents from regressing.
        Assumptions: ``graphene_django.views.get_operation_ast`` is the
            single import the view uses.
        Expectations: The wrapped function is invoked exactly one time
            during a single ``execute_graphql_request`` call.
        """
        from graphene_django import views as views_module

        original = views_module.get_operation_ast
        call_count = {"n": 0}

        def counting_get_operation_ast(*args, **kwargs):
            call_count["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(
            views_module, "get_operation_ast", counting_get_operation_ast
        )

        view = self._make_view()
        request = self._build_request("post")
        view.execute_graphql_request(
            request,
            data={},
            query="{ test }",
            variables=None,
            operation_name=None,
            show_graphiql=False,
        )
        assert call_count["n"] == 1, (
            f"expected exactly one get_operation_ast call, got {call_count['n']}"
        )

    def test_init_with_middleware_setting_none_does_not_raise(self, monkeypatch):
        """
        Name: __init__ with MIDDLEWARE=None (B3 pin)
        Description: ``GraphQLView.__init__`` must tolerate
            ``graphene_settings.MIDDLEWARE = None`` without raising
            ``TypeError``. The original PR dropped the ``if middleware is
            not None`` guard, which would have caused
            ``list(instantiate_middleware(None))`` to fail.
        Assumptions: ``graphene_settings.MIDDLEWARE`` is a publicly-overridable
            setting that may legitimately be ``None``.
        Expectations: Constructing the view succeeds and ``view.middleware``
            equals the class default (``None``).
        """
        from graphene_django.views import GraphQLView

        from .schema_view import schema

        monkeypatch.setattr(
            "graphene_django.views.graphene_settings.MIDDLEWARE", None
        )

        view = GraphQLView(schema=schema)
        assert view.middleware is None
