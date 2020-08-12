class MissingType(object):
    pass


try:
    # Postgres fields are only available in Django with psycopg2 installed
    # and we cannot have psycopg2 on PyPy
    from django.contrib.postgres.fields import (
        ArrayField,
        HStoreField,
        JSONField as PGJSONField,
        RangeField,
    )
except ImportError:
    ArrayField, HStoreField, PGJSONField, RangeField = (MissingType,) * 4

try:
    # JSONField is only available from Django 3.1
    from django.db.models import JSONField
except ImportError:
    JSONField = MissingType
