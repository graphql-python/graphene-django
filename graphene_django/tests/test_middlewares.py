import json
import logging
import graphene
import mock
from django.http.response import HttpResponse
from django.test import RequestFactory
from graphene.test import Client

from .models import Reporter
from .. import DjangoObjectType
from ..middlewares import ClientErrorLogMiddleware


class ReporterType(DjangoObjectType):
    class Meta:
        model = Reporter
        fields = "__all__"


class Query(graphene.ObjectType):
    reporter = graphene.Field(ReporterType)

    def resolve_reporter(self, info, **args):
        return Reporter.objects.first()


def test_should_log_error(caplog):
    Reporter.objects.create(last_name="ABA")

    invalid_query = """
        query ReporterQuery {
          reporter {
            invalidAttrName 
          }
        }
    """

    schema = graphene.Schema(query=Query)
    client = Client(schema)
    response = client.execute(invalid_query)

    factory = RequestFactory()
    request = factory.post(
        "/graphql", data=json.dumps(invalid_query), content_type="application/json"
    )

    http_res = HttpResponse(json.dumps(response).encode(), status=400)

    get_response = mock.MagicMock()
    get_response.return_value = http_res

    middleware = ClientErrorLogMiddleware(get_response)
    middleware(request)

    assert len(caplog.records) == 1
    assert caplog.records[0] != "WARNING"
    assert str(response["errors"]) in caplog.text
    assert invalid_query in caplog.text


def test_should_not_log_success(caplog):
    Reporter.objects.create(last_name="ABA")

    valid_query = """
        query ReporterQuery {
          reporter {
            lastName
          }
        }
    """

    schema = graphene.Schema(query=Query)
    client = Client(schema)
    response = client.execute(valid_query)

    factory = RequestFactory()
    request = factory.post(
        "/graphql", data=json.dumps(valid_query), content_type="application/json"
    )

    http_res = HttpResponse(json.dumps(response).encode(), status=200)

    get_response = mock.MagicMock()
    get_response.return_value = http_res

    middleware = ClientErrorLogMiddleware(get_response)
    middleware(request)

    assert len(caplog.records) == 0


def test_should_not_log_non_graphql_error(caplog):
    factory = RequestFactory()
    request = factory.post(
        "/users", data=json.dumps({"name": "Mario"}), content_type="application/json"
    )
    http_res = HttpResponse(
        json.dumps({"errors": ["Got to be Luigi"]}).encode(), status=400
    )

    get_response = mock.MagicMock()
    get_response.return_value = http_res

    middleware = ClientErrorLogMiddleware(get_response)
    middleware(request)

    assert len(caplog.records) == 0
