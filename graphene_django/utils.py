import inspect

from django.db import models
from django.db.models.manager import Manager

from .compat import RelatedObject


# from graphene.utils import LazyList


class LazyList(object):
    pass


try:
    import django_filters  # noqa
    DJANGO_FILTER_INSTALLED = True
except (ImportError, AttributeError):
    # AtributeError raised if DjangoFilters installed with a incompatible Django Version
    DJANGO_FILTER_INSTALLED = False


def get_reverse_fields(model):
    for name, attr in model.__dict__.items():
        # Django =>1.9 uses 'rel', django <1.9 uses 'related'
        related = getattr(attr, 'rel', None) or \
            getattr(attr, 'related', None)
        if isinstance(related, RelatedObject):
            # Hack for making it compatible with Django 1.6
            new_related = RelatedObject(related.parent_model, related.model, related.field)
            new_related.name = name
            yield new_related
        elif isinstance(related, models.ManyToOneRel):
            yield related
        elif isinstance(related, models.ManyToManyRel) and not related.symmetrical:
            yield related


def maybe_queryset(value):
    if isinstance(value, Manager):
        value = value.get_queryset()
    return value


def get_model_fields(options):
    model = options.model
    all_fields = sorted(list(model._meta.fields) +
                        list(model._meta.local_many_to_many))
    if options.reverse_fields:
        reverse_fields = get_reverse_fields(model)
        all_fields += list(reverse_fields)

    return all_fields


def get_related_model(field):
    if hasattr(field, 'rel'):
        # Django 1.6, 1.7
        return field.rel.to
    return field.related_model


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
