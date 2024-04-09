from asgiref.sync import sync_to_async
from django.db import connections
from graphql.type.definition import GraphQLNonNull

from ..utils import is_running_async, is_sync_function
from .exception.formating import wrap_exception
from .sql.tracking import unwrap_cursor, wrap_cursor
from .types import DjangoDebug


class DjangoDebugContext:
    def __init__(self):
        self.debug_result = None
        self.results = []
        self.object = DjangoDebug(sql=[], exceptions=[])
        self.enable_instrumentation()

    def get_debug_result(self):
        if not self.debug_result:
            self.debug_result = self.results
            self.results = []
        return self.on_resolve_all_results()

    def on_resolve_error(self, value):
        if hasattr(self, "object"):
            self.object.exceptions.append(wrap_exception(value))
        return value

    def on_resolve_all_results(self):
        if self.results:
            self.debug_result = None
            return self.get_debug_result()
        self.disable_instrumentation()
        return self.object

    def add_result(self, result):
        if self.debug_result:
            self.results.append(result)

    def enable_instrumentation(self):
        # This is thread-safe because database connections are thread-local.
        for connection in connections.all():
            wrap_cursor(connection, self)

    def disable_instrumentation(self):
        for connection in connections.all():
            unwrap_cursor(connection)


class DjangoDebugMiddleware:
    def resolve(self, next, root, info, **args):
        context = info.context
        django_debug = getattr(context, "django_debug", None)
        if not django_debug:
            if context is None:
                raise Exception("DjangoDebug cannot be executed in None contexts")
            try:
                context.django_debug = DjangoDebugContext()
            except Exception:
                raise Exception(
                    "DjangoDebug need the context to be writable, context received: {}.".format(
                        context.__class__.__name__
                    )
                )
        if info.schema.get_type("DjangoDebug") == info.return_type:
            return context.django_debug.get_debug_result()
        try:
            result = next(root, info, **args)
        except Exception as e:
            return context.django_debug.on_resolve_error(e)
        context.django_debug.add_result(result)
        return result


class DjangoSyncRequiredMiddleware:
    def resolve(self, next, root, info, **args):
        parent_type = info.parent_type
        return_type = info.return_type

        if isinstance(parent_type, GraphQLNonNull):
            parent_type = parent_type.of_type
        if isinstance(return_type, GraphQLNonNull):
            return_type = return_type.of_type

        if any(
            [
                hasattr(parent_type, "graphene_type")
                and hasattr(parent_type.graphene_type._meta, "model"),
                hasattr(return_type, "graphene_type")
                and hasattr(return_type.graphene_type._meta, "model"),
                info.parent_type.name == "Mutation",
            ]
        ):
            if is_sync_function(next) and is_running_async():
                return sync_to_async(next)(root, info, **args)

        return next(root, info, **args)
