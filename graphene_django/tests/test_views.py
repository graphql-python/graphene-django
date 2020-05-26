import json
import pytest

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


j = lambda **kwargs: json.dumps(kwargs)
jl = lambda **kwargs: json.dumps([kwargs])


@pytest.mark.django_db
def test_graphiql_is_enabled(client):
    from django.conf import settings

    response = client.get(url_string(), HTTP_ACCEPT="text/html")

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


@pytest.mark.django_db
def test_qfactor_graphiql(client):

    response = client.get(url_string(query="{test}", HTTP_ACCEPT="text/html",))

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "text/html"


@pytest.mark.django_db
def test_qfactor_json(client):
    response = client.get(url_string(query="{test}", HTTP_ACCEPT="application/json",))

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_get_with_query_param(client):
    response = client.get(url_string(query="{test}"))

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_get_with_variable_values(client):
    response = client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
            HTTP_ACCEPT="application/json",
        )
    )

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World", "shared": "Hello Everyone"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_reports_validation_errors(client):
    response = client.get(url_string(query="{ test, unknownOne, unknownTwo }"))

    assert response.status_code == 400
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [
            {
                "message": 'Cannot query field "unknownOne" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 9}],
            },
            {
                "message": 'Cannot query field "unknownTwo" on type "QueryRoot".',
                "locations": [{"line": 1, "column": 21}],
            },
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_errors_when_missing_operation_name(client):
    response = client.get(
        url_string(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """
        )
    )

    assert response.status_code == 400
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [
            {
                "message": "Must provide operation name if query contains multiple operations."
            }
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_errors_when_sending_a_mutation_via_get(client):
    response = client.get(
        url_string(
            query="""
        mutation TestMutation { writeTest { test } }
        """
        )
    )
    assert response.status_code == 405
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 405
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [
            {"message": "Can only perform a mutation operation from a POST request."}
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_post_with_json_encoding(client):
    response = client.post(url_string(), j(query="{test}"), "application/json")

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_allows_post_with_json_encoding(client):
    response = client.post(
        batch_url_string(), jl(id=1, query="{test}"), "application/json"
    )

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"
    # returns just json as __dict__
    expected_dict = [{"id": 1, "data": {"test": "Hello World"}, "status": 200}]
    # directly compare all key,value for __dict__ -- NOTE responce is list of stuff!
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_batch_fails_if_is_empty(client):
    response = client.post(batch_url_string(), "[]", "application/json")

    assert response.status_code == 400
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [{"message": "Received an empty list in the batch request."}]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_sending_a_mutation_via_post(client):
    response = client.post(
        url_string(),
        j(query="mutation TestMutation { writeTest { test } }"),
        "application/json",
    )

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"writeTest": {"test": "Hello World"}}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_allows_post_with_url_encoding(client):
    response = client.post(
        url_string(),
        urlencode(dict(query="{test}")),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_supports_post_json_query_with_string_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = [{"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}]
    # directly compare all key,value for __dict__ -- NOTE responce is list of stuff!
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_supports_post_json_query_with_json_variables(client):
    response = client.post(
        url_string(),
        j(
            query="query helloWho($who: String){ test(who: $who) }",
            variables={"who": "Dolly"},
        ),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = [{"id": 1, "data": {"test": "Hello Dolly"}, "status": 200}]
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_supports_post_url_encoded_query_with_string_variables(client):
    response = client.post(
        url_string(),
        urlencode(
            dict(
                query="query helloWho($who: String){ test(who: $who) }",
                variables=json.dumps({"who": "Dolly"}),
            )
        ),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_supports_post_json_quey_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        j(query="query helloWho($who: String){ test(who: $who) }"),
        "application/json",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_post_url_encoded_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        urlencode(dict(query="query helloWho($who: String){ test(who: $who) }")),
        "application/x-www-form-urlencoded",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_supports_post_raw_text_query_with_get_variable_values(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        "application/graphql",
    )

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello Dolly"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World", "shared": "Hello Everyone"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = [
        {
            "id": 1,
            "data": {"test": "Hello World", "shared": "Hello Everyone"},
            "status": 200,
        }
    ]
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
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

    assert response.status_code == 200
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"test": "Hello World", "shared": "Hello Everyone"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


# inherited/ ???
"""
@pytest.mark.django_db
@pytest.mark.urls("graphene_django.tests.urls_inherited")
def test_inherited_class_with_attributes_works(client):
    inherited_url = "/graphql/inherited/"
    # Check schema and pretty attributes work
    response = client.post(url_string(inherited_url, query="{test}"))
    assert response.status_code == 200
    # returns just json as list of __dict__
    expected_dict = (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict

    # Check graphiql works
    response = client.get(url_string(inherited_url), HTTP_ACCEPT="text/html")
    assert response.status_code == 200
"""


@pytest.mark.django_db
def test_handles_field_errors_caught_by_graphql(client):
    response = client.get(url_string(query="{thrower}"))
    assert response.status_code == 200
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "data": None,
        "errors": [
            {
                "locations": [{"column": 2, "line": 1}],
                "path": ["thrower"],
                "message": "Throws!",
            }
        ],
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_syntax_errors_caught_by_graphql(client):
    response = client.get(url_string(query="syntaxerror"))
    assert response.status_code == 400
    # returns just json as list of __dict__
    expected_dict = {
        "errors": [
            {
                "locations": [{"column": 1, "line": 1}],
                "message": "Syntax Error GraphQL (1:1) "
                'Unexpected Name "syntaxerror"\n\n1: syntaxerror\n   ^\n',
            }
        ]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_errors_caused_by_a_lack_of_query(client):
    response = client.get(url_string())

    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "Must provide query string."}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_not_expected_json_bodies(client):
    response = client.post(url_string(), "[]", "application/json")

    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [{"message": "The received data is not a valid JSON query."}]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_invalid_json_bodies(client):
    response = client.post(url_string(), "[oh}", "application/json")

    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "POST body sent invalid JSON."}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_django_request_error(client, monkeypatch):
    def mocked_read(*args):
        raise IOError("foo-bar")

    monkeypatch.setattr("django.http.request.HttpRequest.read", mocked_read)

    valid_json = json.dumps(dict(foo="bar"))
    response = client.post(url_string(), valid_json, "application/json")

    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "foo-bar"}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_plain_post_text(client):
    response = client.post(
        url_string(variables=json.dumps({"who": "Dolly"})),
        "query helloWho($who: String){ test(who: $who) }",
        "text/plain",
    )
    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "Must provide query string."}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_poorly_formed_variables(client):
    response = client.get(
        url_string(
            query="query helloWho($who: String){ test(who: $who) }", variables="who:You"
        )
    )
    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "Variables are invalid JSON."}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_unsupported_http_methods(client):
    response = client.put(url_string(query="{test}"))

    assert response.status_code == 405
    assert response["Allow"] == "GET, POST"
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {
        "errors": [{"message": "GraphQL only supports GET and POST requests."}]
    }
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_handles_incomplete_json_bodies(client):
    response = client.post(url_string(), '{"query":', "application/json")

    assert response.status_code == 400
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"errors": [{"message": "POST body sent invalid JSON."}]}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


@pytest.mark.django_db
def test_passes_request_into_context_request(client):
    response = client.get(url_string(query="{request}", q="testing"))

    assert response.status_code == 200
    # returns just json as list of __dict__
    assert response["Content-Type"].split(";")[0] == "application/json"
    expected_dict = {"data": {"request": "testing"}}
    # directly compare all key,value for __dict__
    assert response.json() == expected_dict


# pretty() -- comparing as string
@pytest.mark.django_db
@pytest.mark.urls("graphene_django.tests.urls_pretty")
def test_supports_pretty_printing(client):
    response = client.get(url_string(query="{test}"))

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


@pytest.mark.django_db
def test_supports_pretty_printing_by_request(client):
    response = client.get(url_string(query="{test}", pretty="1"))

    assert response.status_code == 200
    assert response["Content-Type"].split(";")[0] == "application/json"

    assert response.content.decode() == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


# GraphQL SPEC:
# TODO: more mutations and somesucriptions
# TODO: fragment
# TODO: META __typename
# Additions:
# META AUTH
# ?not working? CDN not static/ for DEBUG
