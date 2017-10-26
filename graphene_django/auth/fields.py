
from django.core.exceptions import PermissionDenied

from .utils import has_perm
from ..fields import DjangoConnectionField


class AuthDjangoConnectionField(DjangoConnectionField):

    @classmethod
    def connection_resolver(cls, resolver, connection, default_manager, max_limit,
                            enforce_first_or_last, root, info, **args):
        """
        Resolve the required connection if the user in context has the permission required. If the user
        does not have the required permission then returns a *Permission Denied* to the request.
        """
        assert self._permissions is not None
        if has_perm(self._permissions, info.context) is not True:
            print(DjangoConnectionField)
            return DjangoConnectionField.connection_resolver(
                resolver, connection, [PermissionDenied('Permission Denied'), ], max_limit,
                enforce_first_or_last, root, info, **args)
        return super(AuthDjangoConnectionField, self).connection_resolver(
            cls, resolver, connection, default_manager, max_limit,
            enforce_first_or_last, root, info, **args)
