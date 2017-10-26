from functools import wraps
from django.core.exceptions import PermissionDenied
from ..fields import DjangoConnectionField

from .utils import has_perm


def node_require_permission(permissions):
    def require_permission_decorator(func):
        @wraps(func)
        def func_wrapper(cls, info, id):
            if has_perm(permissions=permissions, context=info.context):
                return func(cls, info, id)
            raise PermissionDenied('Permission Denied')
        return func_wrapper
    return require_permission_decorator


def mutation_require_permission(permissions):
    def require_permission_decorator(func):
        @wraps(func)
        def func_wrapper(cls, root, info, **input):
            if has_perm(permissions=permissions, context=info.context):
                return func(cls, root, info, **input)
            return cls(errors=PermissionDenied('Permission Denied'))
        return func_wrapper
    return require_permission_decorator


def connection_require_permission(permissions):
    def require_permission_decorator(func):
        @wraps(func)
        def func_wrapper(
                cls, resolver, connection, default_manager, max_limit,
                enforce_first_or_last, root, info, **args):
            if has_perm(permissions=permissions, context=info.context):
                print("Has Perms")
                return func(
                    cls, resolver, connection, default_manager, max_limit,
                    enforce_first_or_last, root, info, **args)
            return DjangoConnectionField.connection_resolver(
                resolver, connection, [PermissionDenied('Permission Denied'), ], max_limit,
                enforce_first_or_last, root, info, **args)
        return func_wrapper
    return require_permission_decorator
