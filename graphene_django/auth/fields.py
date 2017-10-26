from django.core.exceptions import PermissionDenied
from graphene_django.filter.fields import DjangoFilterConnectionField
from graphene_django.fields import DjangoConnectionField


class AuthDjangoFilterConnectionField(DjangoFilterConnectionField):
    _permission = ''

    @classmethod
    def has_perm(cls, context):
        if context is None:
            return False
        if type(context) is dict:
            user = context.get('user', None)
            if user is None:
                return False
        else:
            user = context.user
            if user.is_authenticated() is False:
                return False

        if type(cls._permission) is tuple:
            for permission in cls._permission:
                if not user.has_perm(permission):
                    return False
        if type(cls._permission) is str:
            if not user.has_perm(cls._permission):
                return False
        return True

    def connection_resolver(self, resolver, connection, default_manager, filterset_class, filtering_args,
                            root, args, context, info):
        if self.has_perm(context) is not True:
            return DjangoConnectionField.connection_resolver(
                resolver, connection, [PermissionDenied('Permission Denied'), ], root, args, context, info)
        return super(AuthDjangoFilterConnectionField, self).connection_resolver(
            resolver, connection, default_manager, filterset_class, filtering_args,
            root, args, context, info)
