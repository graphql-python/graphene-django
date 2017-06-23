class MissingType(object):
    pass


try:
    # Postgres fields are only available in Django with psycopg2 installed
    # and we cannot have psycopg2 on PyPy
    from django.contrib.postgres.fields import ArrayField, HStoreField, RangeField
except ImportError:
    ArrayField, HStoreField, JSONField, RangeField = (MissingType, ) * 4


try:
    # Postgres fields are only available in Django 1.9+
    from django.contrib.postgres.fields import JSONField
except ImportError:
    JSONField = MissingType
