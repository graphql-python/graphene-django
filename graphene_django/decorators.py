# coding: utf-8
from functools import wraps
from django.http import HttpResponseForbidden


def has_perms(permissions):
    """
    Check if have user logged and permissions to see some value

    Example:
        class CityNode(DjangoObjectType):
            class Meta(object):
                interfaces = (relay.Node,)
                model = City
                only_fields = (
                    'name', 'locality', 'slug', 'state', 'active',
                )

            @has_perms(["django_city_app.can_see_location"])
            def resolve_location(self, args, context, info):
                return self.locality.pos

    Args:
        permissions: ["django_app.permission_codename",]
    """
    def decorator(method):
        if callable(permissions):
            method.permissions = []
        else:
            method.permissions = permissions

        @wraps(method)
        def wrapper(*args, **kwargs):
            context = kwargs.get('context', dict(zip(method.func_code.co_varnames,
                                                     args)).get('context', None))
            if not context:
                return HttpResponseForbidden('Forbidden. No context, no access.')
            try:
                user = context.user
            except AttributeError:
                return HttpResponseForbidden('Forbidden. No request.')

            if method.permissions and not user.has_perms(method.permissions):
                return HttpResponseForbidden('Forbidden. User without access')
            return method(*args, **kwargs)
        return wrapper

    if callable(permissions):
        return decorator(permissions)

    return decorator
