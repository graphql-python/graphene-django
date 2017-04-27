import collections
from graphene_django import converter, utils

from graphene.types.utils import merge
from graphene.utils.is_base_type import is_base_type


def convert_fields(model, only_fields, exclude_fields):
    model_fields = utils.get_model_fields(model=model)
    fields = collections.OrderedDict()

    for name, field in model_fields:
        is_not_in_only = only_fields and name not in only_fields
        is_already_created = name in model_fields
        is_excluded = name in exclude_fields or is_already_created
        # https://docs.djangoproject.com/en/1.10/ref/models/fields/#django.db.models.ForeignKey.related_query_name
        is_no_backref = str(name).endswith('+')
        if is_not_in_only or is_excluded or is_no_backref:
            # We skip this field if we specify only_fields and is not
            # in there. Or when we exclude this field in exclude_fields.
            # Or when there is no back reference.
            continue
        converted = converter.convert_django_field(field, None)
        if not converted:
            continue
        
        fields[name] = converted
        print(fields)
    return fields


class DjangoModelInputMeta(type):

    @staticmethod
    def __new__(cls, name, bases, attrs):
        # We'll get called also for non-user classes like DjangoModelInput. Only
        # kick in when called for a sub-class.
        if not is_base_type(bases, DjangoModelInputMeta):
            return type.__new__(cls, name, bases, attrs)

        # Pop Meta info. Must be removed from class, otherwise graphene will
        # complain.
        meta = attrs.pop('Meta')
        if not hasattr(meta, 'exclude_fields'):
            setattr(meta, 'exclude_fields', ())
        if not hasattr(meta, 'only_fields'):
            setattr(meta, 'only_fields', ())
        fields = convert_fields(model=meta.model, only_fields=meta.only_fields, exclude_fields=meta.exclude_fields)
        attrs = merge(attrs, fields)

        return type.__new__(cls, name, bases, attrs)


class DjangoModelInput(metaclass=DjangoModelInputMeta):
    """
    Derive a mutation's Input class from this and define a meta class with 
    `model` and `only_fields` members. This will populate the input class
    with the converted django members.
    """
    pass