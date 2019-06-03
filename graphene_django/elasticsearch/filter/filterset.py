"""Fields"""
from collections import OrderedDict

from elasticsearch_dsl import Q
from django.utils import six
from django_filters.filterset import BaseFilterSet

from .filters import StringFilterES


class FilterSetESOptions(object):
    """Basic FilterSetES options to Metadata"""
    def __init__(self, options=None):
        """
        The field option is combined with the index to automatically generate
        filters.
        """
        self.index = getattr(options, 'index', None)
        self.model = self.index._doc_type.model if self.index else None


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

        new_class._meta = FilterSetESOptions(getattr(new_class, 'Meta', None))
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
    def __init__(self, data, queryset, request):
        """
        Receiving params necessaries to resolved the data
        :param data: argument passed to query
        :param queryset: a ES queryset
        :param request: the context of request
        """
        self.data = data
        self.es_query = queryset
        self.request = request

    @property
    def qs(self):
        """Returning ES queryset as QS"""
        query_base = self.generate_q()
        self.es_query.apply_query("query", query_base)
        self.es_query.apply_query("source", ["id"])
        return self.es_query

    def generate_q(self):
        """
        Generate a query for each filter.
        :return: Generates a super query with bool as root, and combines all sub-queries from each argument.
        """
        query_base = Q("bool")
        for name, filter_es in six.iteritems(self.declared_filters):
            query_filter = filter_es.get_q(self.data)
            if query_filter is not None:
                query_base += query_filter
        return query_base
