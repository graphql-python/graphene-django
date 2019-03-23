import inspect

from django.db import models
from graphene.types.scalars import Int
from neomodel import (
    NodeSet,
    StructuredNode,
)


pagination_params = dict(first=Int(default_value=100), last=Int())
# from graphene.utils import LazyList

def is_parent_set(info):
    if hasattr(info.parent_type.graphene_type._meta, 'know_parent_fields'):
        options = info.parent_type.graphene_type._meta.know_parent_fields
        assert isinstance(options, (list, tuple)), \
            "know_parent_fields should be list or tuple"
        return info.field_name in options
    return False


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
    if isinstance(value, NodeSet):
        value = value.filter()
    return value


def get_model_fields(model):
    local_fields = [
        (field[0], field[1])
        for field in sorted(
            model.defined_properties().items()
        )
    ]

    # Make sure we don't duplicate local fields with "reverse" version
    local_field_names = [field[0] for field in local_fields]
    reverse_fields = get_reverse_fields(model, local_field_names)

    all_fields = local_fields + list(reverse_fields)

    return all_fields


def is_valid_neomodel_model(model):
    return inspect.isclass(model) and issubclass(model, StructuredNode)


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
