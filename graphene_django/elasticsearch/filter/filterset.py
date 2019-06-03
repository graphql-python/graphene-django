"""Fields"""
import copy
from collections import OrderedDict
from elasticsearch_dsl import Q
from django_elasticsearch_dsl import ObjectField, StringField, TextField
from django.utils import six
from django_filters.utils import try_dbfield
from django_filters.filterset import BaseFilterSet

from .filters import StringFilterES

# Basic conversion from ES fields to FilterES fields
FILTER_FOR_ESFIELD_DEFAULTS = {
    StringField: {'filter_class': StringFilterES},
    TextField: {'filter_class': StringFilterES},
}


class FilterSetESOptions(object):
    """Basic FilterSetES options to Metadata"""
    def __init__(self, options=None):
        """
        The field option is combined with the index to automatically generate
        filters.

        The includes option accept two kind of syntax:
                - a list of field names
                - a dictionary of field names mapped to a list of expressions

        Example:
             class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    includes = ['username', 'last_login']

            or

            class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    includes = {
                            'username': ['term']
                            'last_login': ['lte', 'gte]
                            }

        The list syntax will create an filter with a behavior by default,
        for each field included in includes. The dictionary syntax will
        create a filter for each expression declared for its corresponding
        field.

         Note that the generated filters will not overwrite filters
         declared on the FilterSet.

         Example:
            class UserFilter(FilterSetES):
                username = StringFieldES('username', core_type='text', expr=['partial'])
                class Meta:
                    index = UserIndex
                    includes = {
                            'username': ['term', 'word']
                            }

        A query with username as a parameter, will match those words with the
        username value as substring

        The excludes option accept a list of field names.

        Example:
             class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    excludes = ['username', 'last_login']

            or

        It is necessary to provide includes or excludes. You cant provide a excludes empty to generate all fields
        """
        self.index = getattr(options, 'index', None)
        self.includes = getattr(options, 'includes', None)
        self.excludes = getattr(options, 'excludes', None)

        if self.index is None:
            raise ValueError('You need provide a Index in Meta.')
        if self.excludes is None and self.includes is None:
            raise ValueError('You need provide includes or excludes field in Meta.')

        self.model = self.index._doc_type.model if self.index else None


class FilterSetESMetaclass(type):
    """Captures the meta class of the filterSet class."""

    def __new__(mcs, name, bases, attrs):
        """Get filters declared explicitly in the class"""

        declared_filters = mcs.get_declared_filters(bases, attrs)
        attrs['declared_filters'] = declared_filters

        new_class = super(FilterSetESMetaclass, mcs).__new__(mcs, name, bases, attrs)

        if issubclass(new_class, BaseFilterSet):
            new_class._meta = FilterSetESOptions(getattr(new_class, 'Meta', None))
            base_filters = OrderedDict()
            for name, filter_field in six.iteritems(declared_filters):
                base_filters.update(filter_field.fields)

            meta_filters = mcs.get_meta_filters(new_class._meta)
            base_filters.update(OrderedDict(meta_filters))
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

    @classmethod
    def get_meta_filters(mcs, meta):
        """
        Get filters from Meta configuration
        :return: Field extracted from index and from the FilterSetES.
        """
        index_fields = mcs.get_index_fields(meta)

        meta_filters = []
        for name, index_field, data in index_fields:

            if isinstance(index_field, ObjectField):
                meta_filters.extend((name, mcs.get_filter_object(name, index_field, data)))
            else:
                meta_filters.append((name, mcs.get_filter_exp(name, index_field, data)))

        return meta_filters

    @classmethod
    def get_index_fields(mcs, meta):
        """
        Get fields from index that appears in the meta class configuration of the filter_set
        :return: Tuple of (name, field, lookup_expr) describing name of the field, ES class of the field and lookup_expr
        """
        index_fields = meta.index._doc_type._fields()
        meta_includes = meta.includes
        meta_excludes = meta.excludes

        if isinstance(meta_includes, dict):
            # The lookup_expr are defined in Meta
            filter_fields = [(name, index_fields[name], data) for name, data in meta_includes.items()]
        elif meta_includes is not None:
            # The lookup_expr are not defined
            filter_fields = [(name, index_fields[name], None) for name in meta_includes]
        else:
            # No `includes` are declared in meta, so all not `excludes` fields from index will be converted to filters
            filter_fields = [(name, field, None) for name, field in index_fields.items() if name not in meta_excludes]
        return filter_fields

    @classmethod
    def get_filter_object(mcs, name, field, data):
        """Get filters from ObjectField"""
        index_fields = []

        properties = field._doc_class._doc_type.mapping.properties._params.get('properties', {})

        for inner_name, inner_field in properties.items():

            if data and inner_name not in data:
                # This inner field is not filterable
                continue
            inner_data = data[inner_name] if data else None

            index_fields.append(mcs.get_filter_exp(inner_name, inner_field, inner_data, root=name))

        return index_fields

    @classmethod
    def get_filter_exp(mcs, name, field, data=None, root=None):
        """Initialize filter"""
        field_data = try_dbfield(FILTER_FOR_ESFIELD_DEFAULTS.get, field.__class__) or {}
        filter_class = field_data.get('filter_class')

        extra = field_data.get('extra', {})
        kwargs = copy.deepcopy(extra)

        # Get lookup_expr from configuration
        if data and 'lookup_exprs' in data:
            if 'lookup_exprs' in kwargs:
                kwargs['lookup_exprs'] = set(kwargs['lookup_exprs']).intersection(set(data['lookup_exprs']))
            else:
                kwargs['lookup_exprs'] = set(data['lookup_exprs'])
        elif 'lookup_exprs' in kwargs:
            kwargs['lookup_exprs'] = set(kwargs['lookup_exprs'])

        kwargs['name'], kwargs['attr'] = mcs.get_name(name, root, data)
        return filter_class(**kwargs)

    @staticmethod
    def get_name(name, root, data):
        """Get names of the field and the path to resolve it"""
        field_name = data.get('name', None) if data else None
        attr = data.get('attr', None) if data else None
        if not field_name:
            field_name = '{root}_{name}'.format(root=root, name=name) if root else name
        if not attr:
            attr = '{root}.{name}'.format(root=root, name=name) if root else name
        return field_name, attr


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
        for name, filter_es in six.iteritems(self.base_filters):
            query_filter = filter_es.get_q(self.data) if len(self.data) else None
            if query_filter is not None:
                query_base += query_filter
        return query_base
