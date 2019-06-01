"""Fields"""
from collections import OrderedDict
from django.utils import six
from django_filters.filterset import BaseFilterSet

from .filters import StringFilterES


class FilterSetESMetaclass(type):
    """Captures the meta class of the filterSet class."""

    def __new__(mcs, name, bases, attrs):
        """Get filters declared explicitly in the class"""

        declared_filters = mcs.get_declared_filters(bases, attrs)
        attrs['declared_filters'] = declared_filters

        new_class = super(FilterSetESMetaclass, mcs).__new__(mcs, name, bases, attrs)

        if issubclass(new_class, BaseFilterSet):
            base_filters = OrderedDict()
            for name, filter_field in six.iteritems(declared_filters):
                base_filters.update(filter_field.fields)
            new_class.base_filters = base_filters

        return new_class

    @classmethod
    def get_declared_filters(mcs, bases, attrs):
        """
        Get the filters declared in the class.
        :param bases: base classes of the current class
        :param attrs: attributes captured to be included as metadata
        :return: An OrderedDict of filter fields declared in the class as static fields.
        """

        # List of filters declared in the class as static fields.
        filters = [
            (filter_name, attrs.pop(filter_name))
            for filter_name, obj in list(attrs.items())
            if isinstance(obj, StringFilterES)
        ]

        # Merge declared filters from base classes
        for base in reversed(bases):
            if hasattr(base, 'declared_filters'):
                filters = [(name, field) for name, field in base.declared_filters.items() if name not in attrs] \
                          + filters

        return OrderedDict(filters)


class FilterSetES(six.with_metaclass(FilterSetESMetaclass, object)):
    """FilterSet specific for ElasticSearch."""
    pass
