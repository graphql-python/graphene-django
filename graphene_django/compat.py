class MissingType:
    def __init__(self, *args, **kwargs):
        pass


try:
    # Postgres fields are only available in Django with psycopg2 installed
    # and we cannot have psycopg2 on PyPy
    from django.contrib.postgres.fields import (
        IntegerRangeField,
        ArrayField,
        HStoreField,
        RangeField,
    )
except ImportError:
    IntegerRangeField, ArrayField, HStoreField, RangeField = (MissingType,) * 4
