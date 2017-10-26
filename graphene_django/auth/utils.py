""""
Auth utils module.

Define some functios to authorize user to user mutations or nodes.
"""


def is_related_to_user(object_instance, user, field):
    """Return True when the object_instance is related to user."""
    user_instance = getattr(object_instance, field, None)
    if user:
        if user_instance == user:
            return True
    return False


def is_authorized_to_mutate_object(model, user, id, field):
    """Return True when the when the user is unauthorized."""
    object_instance = model.objects.get(pk=id)
    if is_related_to_user(object_instance, user, field):
        return True
    return False


def has_perm(permissions, context):
    """
    Validates if the user in the context has the permission required.
    """
    assert permissions
    if context is None:
        return False
    user = context.user
    if user.is_authenticated() is False:
        return False

    for permission in permissions:
        if not user.has_perm(permission):
            return False
    return True
