import inspect
import json
import re

import six
from django.db import connection, transaction
from django.http import HttpResponse, HttpResponseNotAllowed
from django.http.response import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import ensure_csrf_cookie

from graphql import get_default_backend
from graphql.error import format_error as format_graphql_error
from graphql.error import GraphQLError
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema
from graphql.execution.middleware import MiddlewareManager

from graphene_django.constants import MUTATION_ERRORS_FLAG
from graphene_django.utils.utils import set_rollback

from .settings import graphene_settings


class HttpError(Exception):
    def __init__(self, response, message=None, *args, **kwargs):
        self.response = response
        self.message = message = message or response.content.decode()
        super(HttpError, self).__init__(message, *args, **kwargs)


def get_accepted_content_types(request):
    def qualify(x):
        parts = x.split(";", 1)
        if len(parts) == 2:
            match = re.match(r"(^|;)q=(0(\.\d{,3})?|1(\.0{,3})?)(;|$)", parts[1])
            if match:
                return parts[0].strip(), float(match.group(2))
        return parts[0].strip(), 1

    raw_content_types = request.META.get("HTTP_ACCEPT", "*/*").split(",")
    qualified_content_types = map(qualify, raw_content_types)
    return list(
        x[0] for x in sorted(qualified_content_types, key=lambda x: x[1], reverse=True)
    )


def instantiate_middleware(middlewares):
    for middleware in middlewares:
        if inspect.isclass(middleware):
            yield middleware()
            continue
        yield middleware


class GraphQLView(View):
    graphiql_template = "graphene/graphiql.html"

    # Polyfill for window.fetch.
    whatwg_fetch_version = "3.2.0"
    whatwg_fetch_sri = "sha256-l6HCB9TT2v89oWbDdo2Z3j+PSVypKNLA/nqfzSbM8mo="

    # React and ReactDOM.
    react_version = "16.13.1"
    react_sri = "sha256-yUhvEmYVhZ/GGshIQKArLvySDSh6cdmdcIx0spR3UP4="
    react_dom_sri = "sha256-vFt3l+illeNlwThbDUdoPTqF81M8WNSZZZt3HEjsbSU="

    # The GraphiQL React app.
    graphiql_version = "1.0.3"
    graphiql_sri = "sha256-VR4buIDY9ZXSyCNFHFNik6uSe0MhigCzgN4u7moCOTk="
    graphiql_css_sri = "sha256-LwqxjyZgqXDYbpxQJ5zLQeNcf7WVNSJ+r8yp2rnWE/E="

    # The websocket transport library for subscriptions.
    subscriptions_transport_ws_version = "0.9.17"
    subscriptions_transport_ws_sri = (
        "sha256-kCDzver8iRaIQ/SVlfrIwxaBQ/avXf9GQFJRLlErBnk="
    )

    schema = None
    graphiql = False
    executor = None
    backend = None
    middleware = None
    root_value = None
    pretty = False
    batch = False
    subscription_path = None

    def __init__(
        self,
        schema=None,
        executor=None,
        middleware=None,
        root_value=None,
        graphiql=False,
        pretty=False,
        batch=False,
        backend=None,
        subscription_path=None,
    ):
        if not schema:
            schema = graphene_settings.SCHEMA

        if backend is None:
            backend = get_default_backend()

        if middleware is None:
            middleware = graphene_settings.MIDDLEWARE

        self.schema = self.schema or schema
        if middleware is not None:
            if isinstance(middleware, MiddlewareManager):
                self.middleware = middleware
            else:
                self.middleware = list(instantiate_middleware(middleware))
        self.executor = executor
        self.root_value = root_value
        self.pretty = self.pretty or pretty
        self.graphiql = self.graphiql or graphiql
        self.batch = self.batch or batch
        self.backend = backend
        if subscription_path is None:
            self.subscription_path = graphene_settings.SUBSCRIPTION_PATH

        assert isinstance(
            self.schema, GraphQLSchema
        ), "A Schema is required to be provided to GraphQLView."
        assert not all((graphiql, batch)), "Use either graphiql or batch processing"

    # noinspection PyUnusedLocal
    def get_root_value(self, request):
        return self.root_value

    def get_middleware(self, request):
        return self.middleware

    def get_context(self, request):
        return request

    def get_backend(self, request):
        return self.backend

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        try:
            if request.method.lower() not in ("get", "post"):
                raise HttpError(
                    HttpResponseNotAllowed(
                        ["GET", "POST"], "GraphQL only supports GET and POST requests."
                    )
                )

            data = self.parse_body(request)
            show_graphiql = self.graphiql and self.can_display_graphiql(request, data)

            if show_graphiql:
                return self.render_graphiql(
                    request,
                    # Dependency parameters.
                    whatwg_fetch_version=self.whatwg_fetch_version,
                    whatwg_fetch_sri=self.whatwg_fetch_sri,
                    react_version=self.react_version,
                    react_sri=self.react_sri,
                    react_dom_sri=self.react_dom_sri,
                    graphiql_version=self.graphiql_version,
                    graphiql_sri=self.graphiql_sri,
                    graphiql_css_sri=self.graphiql_css_sri,
                    subscriptions_transport_ws_version=self.subscriptions_transport_ws_version,
                    subscriptions_transport_ws_sri=self.subscriptions_transport_ws_sri,
                    # The SUBSCRIPTION_PATH setting.
                    subscription_path=self.subscription_path,
                    # GraphiQL headers tab,
                    graphiql_header_editor_enabled=graphene_settings.GRAPHIQL_HEADER_EDITOR_ENABLED,
                )

            if self.batch:
                responses = [self.get_response(request, entry) for entry in data]
                result = "[{}]".format(
                    ",".join([response[0] for response in responses])
                )
                status_code = (
                    responses
                    and max(responses, key=lambda response: response[1])[1]
                    or 200
                )
            else:
                result, status_code = self.get_response(request, data, show_graphiql)

            return HttpResponse(
                status=status_code, content=result, content_type="application/json"
            )

        except HttpError as e:
            response = e.response
            response["Content-Type"] = "application/json"
            response.content = self.json_encode(
                request, {"errors": [self.format_error(e)]}
            )
            return response

    def get_response(self, request, data, show_graphiql=False):
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(
            request, data, query, variables, operation_name, show_graphiql
        )

        if getattr(request, MUTATION_ERRORS_FLAG, False) is True:
            set_rollback()

        status_code = 200
        if execution_result:
            response = {}

            if execution_result.errors:
                set_rollback()
                response["errors"] = [
                    self.format_error(e) for e in execution_result.errors
                ]

            if execution_result.invalid:
                status_code = 400
            else:
                response["data"] = execution_result.data

            if self.batch:
                response["id"] = id
                response["status"] = status_code

            result = self.json_encode(request, response, pretty=show_graphiql)
        else:
            result = None

        return result, status_code

    def render_graphiql(self, request, **data):
        return render(request, self.graphiql_template, data)

    def json_encode(self, request, d, pretty=False):
        if not (self.pretty or pretty) and not request.GET.get("pretty"):
            return json.dumps(d, separators=(",", ":"))

        return json.dumps(d, sort_keys=True, indent=2, separators=(",", ": "))

    def parse_body(self, request):
        content_type = self.get_content_type(request)

        if content_type == "application/graphql":
            return {"query": request.body.decode()}

        elif content_type == "application/json":
            # noinspection PyBroadException
            try:
                body = request.body.decode("utf-8")
            except Exception as e:
                raise HttpError(HttpResponseBadRequest(str(e)))

            try:
                request_json = json.loads(body)
                if self.batch:
                    assert isinstance(request_json, list), (
                        "Batch requests should receive a list, but received {}."
                    ).format(repr(request_json))
                    assert (
                        len(request_json) > 0
                    ), "Received an empty list in the batch request."
                else:
                    assert isinstance(
                        request_json, dict
                    ), "The received data is not a valid JSON query."
                return request_json
            except AssertionError as e:
                raise HttpError(HttpResponseBadRequest(str(e)))
            except (TypeError, ValueError):
                raise HttpError(HttpResponseBadRequest("POST body sent invalid JSON."))

        elif content_type in [
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]:
            return request.POST

        return {}

    def execute_graphql_request(
        self, request, data, query, variables, operation_name, show_graphiql=False
    ):
        if not query:
            if show_graphiql:
                return None
            raise HttpError(HttpResponseBadRequest("Must provide query string."))

        try:
            backend = self.get_backend(request)
            document = backend.document_from_string(self.schema, query)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        if request.method.lower() == "get":
            operation_type = document.get_operation_type(operation_name)
            if operation_type and operation_type != "query":
                if show_graphiql:
                    return None

                raise HttpError(
                    HttpResponseNotAllowed(
                        ["POST"],
                        "Can only perform a {} operation from a POST request.".format(
                            operation_type
                        ),
                    )
                )

        try:
            extra_options = {}
            if self.executor:
                # We only include it optionally since
                # executor is not a valid argument in all backends
                extra_options["executor"] = self.executor

            options = {
                "root_value": self.get_root_value(request),
                "variable_values": variables,
                "operation_name": operation_name,
                "context_value": self.get_context(request),
                "middleware": self.get_middleware(request),
            }
            options.update(extra_options)

            operation_type = document.get_operation_type(operation_name)
            if operation_type == "mutation" and (
                graphene_settings.ATOMIC_MUTATIONS is True
                or connection.settings_dict.get("ATOMIC_MUTATIONS", False) is True
            ):
                with transaction.atomic():
                    result = document.execute(**options)
                    if getattr(request, MUTATION_ERRORS_FLAG, False) is True:
                        transaction.set_rollback(True)
                return result

            return document.execute(**options)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

    @classmethod
    def can_display_graphiql(cls, request, data):
        raw = "raw" in request.GET or "raw" in data
        return not raw and cls.request_wants_html(request)

    @classmethod
    def request_wants_html(cls, request):
        accepted = get_accepted_content_types(request)
        accepted_length = len(accepted)
        # the list will be ordered in preferred first - so we have to make
        # sure the most preferred gets the highest number
        html_priority = (
            accepted_length - accepted.index("text/html")
            if "text/html" in accepted
            else 0
        )
        json_priority = (
            accepted_length - accepted.index("application/json")
            if "application/json" in accepted
            else 0
        )

        return html_priority > json_priority

    @staticmethod
    def get_graphql_params(request, data):
        query = request.GET.get("query") or data.get("query")
        variables = request.GET.get("variables") or data.get("variables")
        id = request.GET.get("id") or data.get("id")

        if variables and isinstance(variables, six.text_type):
            try:
                variables = json.loads(variables)
            except Exception:
                raise HttpError(HttpResponseBadRequest("Variables are invalid JSON."))

        operation_name = request.GET.get("operationName") or data.get("operationName")
        if operation_name == "null":
            operation_name = None

        return query, variables, operation_name, id

    @staticmethod
    def format_error(error):
        if isinstance(error, GraphQLError):
            return format_graphql_error(error)

        return {"message": six.text_type(error)}

    @staticmethod
    def get_content_type(request):
        meta = request.META
        content_type = meta.get("CONTENT_TYPE", meta.get("HTTP_CONTENT_TYPE", ""))
        return content_type.split(";", 1)[0].lower()
