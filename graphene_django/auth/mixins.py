from django.core.exceptions import PermissionDenied


class AuthNodeMixin():
    _permission = ''

    @classmethod
    def get_node(cls, id, context, info):

        def has_perm(object_instance):
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

        try:
            object_instance = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return None

        if has_perm(object_instance):
            return object_instance
        return PermissionDenied('Permission Denied')


class AuthMutationMixin():
    _permission = ''

    @classmethod
    def has_permision(cls, context):
        if context is None:
            return PermissionDenied('Permission Denied')
        if type(context) is dict:
            user = context.get('user', None)
            if user is None:
                return PermissionDenied('Permission Denied')
        else:
            user = context.user
            if user.is_authenticated() is False:
                return PermissionDenied('Permission Denied')

        if type(cls._permission) is tuple:
            for permission in cls._permission:
                if not user.has_perm(permission):
                    return PermissionDenied('Permission Denied')
            return True
        if type(cls._permission) is str:
            if user.has_perm(cls._permission):
                return True
        return PermissionDenied('Permission Denied')
