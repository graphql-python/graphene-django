class MissingType(object):
    pass


try:
    # Postgres fields are only available in Django with psycopg2 installed
    # and we cannot have psycopg2 on PyPy
    from django.contrib.postgres.fields import (
        ArrayField,
        HStoreField,
        JSONField,
        RangeField,
        DateTimeRangeField,
        DateRangeField,
        IntegerRangeField,
        BigIntegerRangeField,
        FloatRangeField,
        DecimalRangeField
    )
except ImportError:
    ArrayField, HStoreField, JSONField, RangeField = (MissingType,) * 4
