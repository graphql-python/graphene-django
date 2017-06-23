class MissingType(object):
    pass


try:
    from django.db.models.related import RelatedObject
except:
    # Improved compatibility for Django 1.6
    RelatedObject = MissingType


try:
    # Postgres fields are only available in Django 1.9+
    from django.contrib.postgres.fields import JSONField
except ImportError:
    JSONField = MissingType
