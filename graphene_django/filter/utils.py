import six

from .filterset import custom_filterset_factory, setup_filterset
from functools import reduce
from neomodel import Q

def get_filterset_class(filterset_class, **meta):
    """Get the class to be used as the FilterSet"""
    if filterset_class:
        # If were given a FilterSet class, then set it up and
        # return it
        return setup_filterset(filterset_class)
    return custom_filterset_factory(**meta)


def make_qs(filters):
    relationship_filters = {}
    for item in filters.items():
        if item[0].endswith('__equal'):
            filters.pop(item[0])
            filters[item[0].split("__")[0]] = item[1]
        elif item[0].endswith('__has'):
            relationship_filters[item[0].split("__")[0]] = item[1]
    for item in relationship_filters.items():
        filters.pop(item[0]+'__has')
    base_filters = reduce(lambda init, nx: init & Q(**{nx[0]: nx[1]}), filters.items(), Q())
    return base_filters, relationship_filters


def get_filtering_args_from_filterset(filterset_class, type):
    from ..forms.converter import convert_form_field
    args = {}
    fields = type._meta.model.defined_properties()
    filterset_fields = filterset_class.Meta.fields or []
    for name in filterset_fields:
        field_type = convert_form_field(fields[name]).Argument()
        field_type.description = "filter"
        for modificator in type._meta.neomodel_filter_fields[name]:
            args["{}__{}".format(name, modificator)] = field_type
    return args
