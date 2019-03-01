import inspect

from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.manager import Manager


# from graphene.utils import LazyList
from graphene.types.resolver import get_default_resolver
from graphene.utils.get_unbound_function import get_unbound_function


class LazyList(object):
    pass


try:
    import django_filters  # noqa

    DJANGO_FILTER_INSTALLED = True
except ImportError:
    DJANGO_FILTER_INSTALLED = False


def get_reverse_fields(model, local_field_names):
    for name, attr in model.__dict__.items():
        # Don't duplicate any local fields
        if name in local_field_names:
            continue

        # Django =>1.9 uses 'rel', django <1.9 uses 'related'
        related = getattr(attr, "rel", None) or getattr(attr, "related", None)
        if isinstance(related, models.ManyToOneRel):
            yield (name, related)
        elif isinstance(related, models.ManyToManyRel) and not related.symmetrical:
            yield (name, related)


def maybe_queryset(value):
    if isinstance(value, Manager):
        value = value.get_queryset()
    return value


def get_model_fields(model):
    local_fields = [
        (field.name, field)
        for field in sorted(
            list(model._meta.fields) + list(model._meta.local_many_to_many)
        )
    ]

    # Make sure we don't duplicate local fields with "reverse" version
    local_field_names = [field[0] for field in local_fields]
    reverse_fields = get_reverse_fields(model, local_field_names)

    all_fields = local_fields + list(reverse_fields)

    return all_fields


def is_valid_django_model(model):
    return inspect.isclass(model) and issubclass(model, models.Model)


def import_single_dispatch():
    try:
        from functools import singledispatch
    except ImportError:
        singledispatch = None

    if not singledispatch:
        try:
            from singledispatch import singledispatch
        except ImportError:
            pass

    if not singledispatch:
        raise Exception(
            "It seems your python version does not include "
            "functools.singledispatch. Please install the 'singledispatch' "
            "package. More information here: "
            "https://pypi.python.org/pypi/singledispatch"
        )

    return singledispatch


def has_permissions(viewer, permissions):
    """
    Verify that at least one permission is accomplished
    :param viewer: Field's viewer
    :param permissions: Field permissions
    :return: True if viewer has permission. False otherwise.
    """
    if not permissions:
        return True
    return any([viewer.has_perm(perm) for perm in permissions])


def resolve_bound_resolver(resolver, root, info, **args):
    """
    Resolve provided resolver
    :param resolver: Explicit field resolver
    :param root: Schema root
    :param info: Schema info
    :param args: Schema args
    :return: Resolved field
    """
    resolver = get_unbound_function(resolver)
    return resolver(root, info, **args)


def auth_resolver(parent_resolver, permissions, attname, default_value, raise_exception, root, info, **args):
    """
    Middleware resolver to check viewer's permissions
    :param parent_resolver: Field resolver
    :param permissions: Field permissions
    :param attname: Field name
    :param default_value: Default value to field if no resolver is provided
    :param raise_exception: If True a PermissionDenied is raised
    :param root: Schema root
    :param info: Schema info
    :param args: Schema args
    :return: Resolved field. None if the viewer does not have permission to access the field.
    """
    # Get viewer from context
    if not hasattr(info.context, 'user'):
        raise PermissionDenied()
    user = info.context.user

    if has_permissions(user, permissions):
        if parent_resolver:
            # A resolver is provided in the class
            return resolve_bound_resolver(parent_resolver, root, info, **args)
        # Get default resolver
        return get_default_resolver()(attname, default_value, root, info, **args)
    elif raise_exception:
        raise PermissionDenied()
    return None
