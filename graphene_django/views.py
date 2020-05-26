import inspect
import json
import re

import six
from django.template.response import TemplateResponse
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.http.response import HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.views import APIView

from graphql import get_default_backend
from graphql.error import format_error as format_graphql_error
from graphql.error import GraphQLError
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema
from graphql.execution.middleware import MiddlewareManager

from graphene_django.settings import graphene_settings


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


class GraphQLView(APIView):
    schema = None
    graphiql = False
    graphiql_headers = False
    executor = None
    backend = None
    middleware = None
    root_value = None
    pretty = False
    batch = False

    def __init__(
        self,
        schema=None,
        executor=None,
        middleware=None,
        root_value=None,
        graphiql=False,
        graphiql_headers=False,
        pretty=False,
        batch=False,
        backend=None,
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
        self.graphiql_headers = self.graphiql_headers or graphiql_headers
        self.batch = self.batch or batch
        self.backend = backend

        assert isinstance(
            self.schema, GraphQLSchema
        ), "A Schema is required to be provided to GraphQLView."
        assert not all(
            (graphiql_headers, graphiql, batch)
        ), "Use either graphiql, graphiql_headers, or batch processing"

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
        # if specified in settings.py:
        # GRAPHENE = {
        # why does this not make it????
        #      'SOURCE': 'cdn'
        # }
        try:
            GET_FROM_CDN = graphene_settings.SOURCE  # get IF it exists
            if GET_FROM_CDN is None:
                # should not need
                GET_FROM_CDN = "static"
        except Exception:
            GET_FROM_CDN = "static"  # this is diconnected by default

        graphiql_arguments = {}
        if GET_FROM_CDN == "cdn":
            graphiql_arguments.update({"graphiql_version": "0.14.0"})
            graphiql_arguments.update({"graphiql_template": "graphene/graphiql.html"})
            graphiql_arguments.update({"react_version": "16.8.6"})
            graphiql_arguments.update({"TEMPLATE_SOURCE": "cdn"})
        elif GET_FROM_CDN == "static":
            graphiql_arguments.update({"graphiql_template": "graphene/graphiql.html"})
            graphiql_arguments.update({"TEMPLATE_SOURCE": "static"})
        else:
            print(
                "The option %s is unsuppored option in setting.  Choose <cdn> or <static>"
                % GET_FROM_CDN
            )

        try:
            if request.method.lower() not in ("get", "post"):
                raise HttpError(
                    HttpResponseNotAllowed(
                        ["GET", "POST"], "GraphQL only supports GET and POST requests."
                    )
                )

            data = self.parse_body(request)
            use_graphiql = False
            if "graphiql_was_used" in request.session:
                if request.session["graphiql_was_used"]:
                    use_graphiql = True

            show_graphiql = self.graphiql and self.can_display_graphiql(request, data)
            show_graphiql_headers = self.graphiql_headers and self.can_display_graphiql(
                request, data
            )

            if show_graphiql:
                request.session["graphiql_was_used"] = True
                request.session.save()

                graphiql_arguments.update({"auth_header": None})
                return self.render_graphiql(request, graphiql_arguments)
            elif show_graphiql_headers:
                # headers [html form & iql -- first http]
                return _get_auth_header(self, request, graphiql_arguments)
            elif self.batch:
                responses = [self.get_response(request, entry) for entry in data]
                result = "[{}]".format(
                    ",".join([response[0] for response in responses])
                )
                status_code = (
                    responses
                    and max(responses, key=lambda response: response[1])[1]
                    or 200
                )
                content_type = "application/json"
            else:
                # not interactive, return data -- curl() or 2nd http (eval graphiql)
                #    From both curl and http, but what about GET (url unit test)
                if not ("HTTP_AUTHORIZATION" in request.META):
                    if "HTTP_AUTHORIZATION" in request.session:
                        # graphiql put in request.session -- restore AUTH
                        request.META.update(
                            {
                                "HTTP_AUTHORIZATION": request.session[
                                    "HTTP_AUTHORIZATION"
                                ]
                            }
                        )
                    else:
                        # no AUTH
                        request.META.update({"HTTP_AUTHORIZATION": None})

                if request.method == "POST":
                    body = dict(self.parse_body(request))
                graphene_arguments = {}
                # output type from URL -- for unit tests
                content_type = "application/json"
                output = request.GET.get("HTTP_ACCEPT", None)
                if output:
                    content_type = output
                else:
                    # get from curl and graphiql
                    if request.method == "POST":
                        if "HTTP_ACCEPT" in body:
                            content_type = request.GET.get("HTTP_ACCEPT", None)
                # URL args (unit test)
                variables = request.GET.get("variables", None)
                if variables:
                    graphene_arguments.update({"variables": variables})
                else:
                    # get from curl and graphiql
                    if request.method == "POST":
                        if "variables" in body:
                            graphene_arguments.update({"variables": body["variables"]})
                query = request.GET.get("query", None)
                if query:
                    graphene_arguments.update({"query": query})
                else:
                    # get from curl and graphiql
                    if request.method == "POST":
                        if "query" in body:
                            graphene_arguments.update({"query": body["query"]})
                        if "operationName" in body:
                            graphene_arguments.update(
                                {"operationName": body["operationName"]}
                            )

                result, status_code = self.get_response(request, graphene_arguments)

            return HttpResponse(
                status=status_code, content=result, content_type=content_type
            )

        except HttpError as e:
            response = e.response
            response["Content-Type"] = "application/json"
            response.content = self.json_encode(
                request, {"errors": [self.format_error(e)]}
            )
            return response

    def get_response(self, request, data):
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(
            request, data, query, variables, operation_name
        )

        status_code = 200
        if execution_result:
            response = {}

            if execution_result.errors:
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

            result = self.json_encode(request, response, pretty=False)
        else:
            result = None

        return result, status_code

    def render_graphiql(self, request, data):
        template = None
        for (key, value) in data.items():
            if key == "graphiql_template":
                template = value

        return TemplateResponse(
            request, template, data
        )  # data is context -- list of dicts

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

        elif (
            content_type == "application/x-www-form-urlencoded"
            or content_type == "multipart/form-data"
        ):
            print("why list???%s" % dict(request.POST))
            args = {}
            items = dict(request.POST)
            for key, value in items.items():
                args[key] = value[0]

            return args

        return {}

    def execute_graphql_request(self, request, data, query, variables, operation_name):
        if not query:
            raise HttpError(HttpResponseBadRequest("Must provide query string."))

        try:
            backend = self.get_backend(request)
            document = backend.document_from_string(self.schema, query)
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        if request.method.lower() == "get":
            operation_type = document.get_operation_type(operation_name)
            if operation_type and operation_type != "query":

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

            return document.execute(
                root_value=self.get_root_value(request),
                variable_values=variables,
                operation_name=operation_name,
                context_value=self.get_context(request),
                middleware=self.get_middleware(request),
                **extra_options
            )
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


def _get_auth_header(iQLView, request, graphiql_arguments):
    from graphene_django.forms import HeaderForm

    # If this is a POST request then process the Form data
    if request.method == "POST":

        # Create a form instance and populate it with data from the request (binding):
        form = HeaderForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required (here we just write it to the model due_back field)
            auth_header = form.cleaned_data["headers"]

            # return extra stuff to put in META tag for graphiql:
            request.session["HTTP_AUTHORIZATION"] = auth_header
            request.session["graphiql_was_used"] = True
            request.session.save()
            graphiql_arguments.update({"auth_header": auth_header})
            return iQLView.render_graphiql(request, graphiql_arguments)

    # If this is a GET (or any other method) create the default form.
    else:
        form = HeaderForm()

    context = {"form": form}

    return TemplateResponse(request, "graphene/header_jwt_auth.html", context)
