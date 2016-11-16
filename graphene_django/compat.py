from django.db import models


class MissingType(object):
    pass


try:
    DurationField = models.DurationField
    UUIDField = models.UUIDField
except AttributeError:
    # Improved compatibility for Django 1.6
    DurationField = MissingType
    UUIDField = MissingType

try:
    from django.db.models.related import RelatedObject
except:
    # Improved compatibility for Django 1.6
    RelatedObject = MissingType


try:
    # Postgres fields are only available in Django 1.8+
    from django.contrib.postgres.fields import ArrayField, HStoreField, RangeField
except ImportError:
    ArrayField, HStoreField, JSONField, RangeField = (MissingType, ) * 4


try:
    # Postgres fields are only available in Django 1.9+
    from django.contrib.postgres.fields import JSONField
except ImportError:
    JSONField = MissingType
