from functools import wraps
from django.core.exceptions import PermissionDenied

from .utils import has_perm, is_authorized_to_mutate_object, is_related_to_user


def node_require_permission(permissions, user_field=None):
    def require_permission_decorator(func):
        @wraps(func)
        def func_wrapper(cls, info, id):
            if user_field:
                user_field is not None
                if is_authorized_to_mutate_object(cls._meta.model, info.context.user, user_field):
                    return func(cls, info, id)
            print("Has Perm Result", has_perm(permissions=permissions, context=info.context))
            if has_perm(permissions=permissions, context=info.context):
                print("Node has persmissions")
                return func(cls, info, id)
            raise PermissionDenied('Permission Denied')
        return func_wrapper
    return require_permission_decorator


def mutation_require_permission(permissions, model=None, user_field=None):
    def require_permission_decorator(func):
        @wraps(func)
        def func_wrapper(cls, root, info, **input):
            if model or user_field:
                assert model is not None and user_field is not None
                object_instance = cls._meta.model.objects.get(pk=id)
                if is_related_to_user(object_instance, info.context.user, user_field):
                    return func(cls, root, info, **input)
            if has_perm(permissions=permissions, context=info.context):
                return func(cls, root, info, **input)
            return cls(errors=PermissionDenied('Permission Denied'))
        return func_wrapper
    return require_permission_decorator
