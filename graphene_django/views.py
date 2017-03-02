import inspect
import json
import re

import six
from django.http import HttpResponse, HttpResponseNotAllowed
from django.http.response import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import ensure_csrf_cookie

from graphql import Source, execute, parse, validate
from graphql.error import format_error as format_graphql_error
from graphql.error import GraphQLError
from graphql.execution import ExecutionResult
from graphql.type.schema import GraphQLSchema
from graphql.utils.get_operation_ast import get_operation_ast

from .settings import graphene_settings


class HttpError(Exception):

    def __init__(self, response, message=None, *args, **kwargs):
        self.response = response
        self.message = message = message or response.content.decode()
        super(HttpError, self).__init__(message, *args, **kwargs)


def get_accepted_content_types(request):
    def qualify(x):
        parts = x.split(';', 1)
        if len(parts) == 2:
            match = re.match(r'(^|;)q=(0(\.\d{,3})?|1(\.0{,3})?)(;|$)',
                             parts[1])
            if match:
                return parts[0], float(match.group(2))
        return parts[0], 1

    raw_content_types = request.META.get('HTTP_ACCEPT', '*/*').split(',')
    qualified_content_types = map(qualify, raw_content_types)
    return list(x[0] for x in sorted(qualified_content_types,
                                     key=lambda x: x[1], reverse=True))


def instantiate_middleware(middlewares):
    for middleware in middlewares:
        if inspect.isclass(middleware):
            yield middleware()
            continue
        yield middleware


class GraphQLView(View):
    graphiql_version = '0.7.8'
    graphiql_template = 'graphene/graphiql.html'

    schema = None
    graphiql = False
    executor = None
    middleware = None
    root_value = None
    pretty = False
    batch = False

    def __init__(self, schema=None, executor=None, middleware=None, root_value=None, graphiql=False, pretty=False,
                 batch=False):
        if not schema:
            schema = graphene_settings.SCHEMA

        if middleware is None:
            middleware = graphene_settings.MIDDLEWARE

        self.schema = schema
        if middleware is not None:
            self.middleware = list(instantiate_middleware(middleware))
        self.executor = executor
        self.root_value = root_value
        self.pretty = pretty
        self.graphiql = graphiql
        self.batch = batch

        assert isinstance(self.schema, GraphQLSchema), 'A Schema is required to be provided to GraphQLView.'
        assert not all((graphiql, batch)), 'Use either graphiql or batch processing'

    # noinspection PyUnusedLocal
    def get_root_value(self, request):
        return self.root_value

    def get_middleware(self, request):
        return self.middleware

    def get_context(self, request):
        return request

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, request, *args, **kwargs):
        try:
            if request.method.lower() not in ('get', 'post'):
                raise HttpError(HttpResponseNotAllowed(['GET', 'POST'], 'GraphQL only supports GET and POST requests.'))

            data = self.parse_body(request)
            show_graphiql = self.graphiql and self.can_display_graphiql(request, data)

            if self.batch:
                responses = [self.get_response(request, entry) for entry in data]
                result = '[{}]'.format(','.join([response[0] for response in responses]))
                status_code = max(responses, key=lambda response: response[1])[1]
            else:
                result, status_code = self.get_response(request, data, show_graphiql)

            if show_graphiql:
                query, variables, operation_name, id = self.get_graphql_params(request, data)
                return self.render_graphiql(
                    request,
                    graphiql_version=self.graphiql_version,
                    query=query or '',
                    variables=json.dumps(variables) or '',
                    operation_name=operation_name or '',
                    result=result or ''
                )

            return HttpResponse(
                status=status_code,
                content=result,
                content_type='application/json'
            )

        except HttpError as e:
            response = e.response
            response['Content-Type'] = 'application/json'
            response.content = self.json_encode(request, {
                'errors': [self.format_error(e)]
            })
            return response

    def get_response(self, request, data, show_graphiql=False):
        query, variables, operation_name, id = self.get_graphql_params(request, data)

        execution_result = self.execute_graphql_request(
            request,
            data,
            query,
            variables,
            operation_name,
            show_graphiql
        )

        status_code = 200
        if execution_result:
            response = {}

            if execution_result.errors:
                response['errors'] = [self.format_error(e) for e in execution_result.errors]

            if execution_result.invalid:
                status_code = 400
            else:
                response['data'] = execution_result.data

            if self.batch:
                response['id'] = id
                response['status'] = status_code

            result = self.json_encode(request, response, pretty=show_graphiql)
        else:
            result = None

        return result, status_code

    def render_graphiql(self, request, **data):
        return render(request, self.graphiql_template, data)

    def json_encode(self, request, d, pretty=False):
        if not (self.pretty or pretty) and not request.GET.get('pretty'):
            return json.dumps(d, separators=(',', ':'))

        return json.dumps(d, sort_keys=True,
                          indent=2, separators=(',', ': '))

    # noinspection PyBroadException
    def parse_body(self, request):
        content_type = self.get_content_type(request)

        if content_type == 'application/graphql':
            return {'query': request.body.decode()}

        elif content_type == 'application/json':
            try:
                request_json = json.loads(request.body.decode('utf-8'))
                if self.batch:
                    assert isinstance(request_json, list), (
                        'Batch requests should receive a list, but received {}.'
                    ).format(repr(request_json))
                    assert len(request_json) > 0, (
                        'Received an empty list in the batch request.'
                    )
                else:
                    assert isinstance(request_json, dict), (
                        'The received data is not a valid JSON query.'
                    )
                return request_json
            except AssertionError as e:
                raise HttpError(HttpResponseBadRequest(str(e)))
            except:
                raise HttpError(HttpResponseBadRequest('POST body sent invalid JSON.'))

        elif content_type in ['application/x-www-form-urlencoded', 'multipart/form-data']:
            return request.POST

        return {}

    def execute(self, *args, **kwargs):
        return execute(self.schema, *args, **kwargs)

    def execute_graphql_request(self, request, data, query, variables, operation_name, show_graphiql=False):
        if not query:
            if show_graphiql:
                return None
            raise HttpError(HttpResponseBadRequest('Must provide query string.'))

        source = Source(query, name='GraphQL request')

        try:
            document_ast = parse(source)
            validation_errors = validate(self.schema, document_ast)
            if validation_errors:
                return ExecutionResult(
                    errors=validation_errors,
                    invalid=True,
                )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

        if request.method.lower() == 'get':
            operation_ast = get_operation_ast(document_ast, operation_name)
            if operation_ast and operation_ast.operation != 'query':
                if show_graphiql:
                    return None

                raise HttpError(HttpResponseNotAllowed(
                    ['POST'], 'Can only perform a {} operation from a POST request.'.format(operation_ast.operation)
                ))

        try:
            return self.execute(
                document_ast,
                root_value=self.get_root_value(request),
                variable_values=variables,
                operation_name=operation_name,
                context_value=self.get_context(request),
                middleware=self.get_middleware(request),
                executor=self.executor,
            )
        except Exception as e:
            return ExecutionResult(errors=[e], invalid=True)

    @classmethod
    def can_display_graphiql(cls, request, data):
        raw = 'raw' in request.GET or 'raw' in data
        return not raw and cls.request_wants_html(request)

    @classmethod
    def request_wants_html(cls, request):
        accepted = get_accepted_content_types(request)
        html_index = accepted.count('text/html')
        json_index = accepted.count('application/json')

        return html_index > json_index

    @staticmethod
    def get_graphql_params(request, data):
        query = request.GET.get('query') or data.get('query')
        variables = request.GET.get('variables') or data.get('variables')
        id = request.GET.get('id') or data.get('id')

        if variables and isinstance(variables, six.text_type):
            try:
                variables = json.loads(variables)
            except:
                raise HttpError(HttpResponseBadRequest('Variables are invalid JSON.'))

        operation_name = request.GET.get('operationName') or data.get('operationName')

        return query, variables, operation_name, id

    @staticmethod
    def format_error(error):
        if isinstance(error, GraphQLError):
            return format_graphql_error(error)

        return {'message': six.text_type(error)}

    @staticmethod
    def get_content_type(request):
        meta = request.META
        content_type = meta.get('CONTENT_TYPE', meta.get('HTTP_CONTENT_TYPE', ''))
        return content_type.split(';', 1)[0].lower()
