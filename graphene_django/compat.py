# For backwards compatibility, we import JSONField to have it available for import via
# this compat module (https://github.com/graphql-python/graphene-django/issues/1428).
# Django's JSONField is available in Django 3.2+ (the minimum version we support)
from django.db.models import JSONField


class MissingType:
    def __init__(self, *args, **kwargs):
        pass


try:
    # Postgres fields are only available in Django with psycopg2 installed
    # and we cannot have psycopg2 on PyPy
    from django.contrib.postgres.fields import (
        ArrayField,
        HStoreField,
        IntegerRangeField,
        RangeField,
    )
except ImportError:
    IntegerRangeField, ArrayField, HStoreField, RangeField = (MissingType,) * 4
