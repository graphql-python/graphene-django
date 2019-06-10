"""Fields"""
import copy
from collections import OrderedDict
from elasticsearch_dsl import Q
from graphene import Enum, InputObjectType, Field, Int, Float
from django_elasticsearch_dsl import (
    StringField,
    TextField,
    BooleanField,
    IntegerField,
    FloatField,
    LongField,
    ShortField,
    DoubleField,
    DateField,
    KeywordField,
    ObjectField,
)
from django.utils import six

from django_filters.utils import try_dbfield
from django_filters.filterset import BaseFilterSet

from graphene_django.elasticsearch.filter.observable import FieldResolverObservable
from .filters import StringFilterES, FilterES, BoolFilterES, NumberFilterES

# Basic conversion from ES fields to FilterES fields
FILTER_FOR_ESFIELD_DEFAULTS = {
    StringField: {"filter_class": StringFilterES},
    TextField: {"filter_class": StringFilterES},
    BooleanField: {"filter_class": BoolFilterES},
    IntegerField: {"filter_class": NumberFilterES},
    FloatField: {"filter_class": NumberFilterES, "argument": Float()},
    LongField: {"filter_class": NumberFilterES, "argument": Int()},
    ShortField: {"filter_class": NumberFilterES, "argument": Int()},
    DoubleField: {"filter_class": NumberFilterES, "argument": Int()},
    DateField: {"filter_class": StringFilterES},
    KeywordField: {"filter_class": StringFilterES},
}


class OrderEnum(Enum):
    """Order enum to desc-asc"""

    asc = "asc"
    desc = "desc"

    @property
    def description(self):
        """Description to order enum"""
        if self == OrderEnum.asc:
            return "Ascendant order"
        return "Descendant order"


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
                        'username': {
                            'field_name': 'graphene_field',
                            'field_name_es': 'elasticsearch_field',
                            'lookup_expressions': ['term', 'contains']
                        }
                    }

        The list syntax will create an filter with a behavior by default,
        for each field included in includes. The dictionary syntax will
        create a filter for each expression declared for its corresponding
        field.

         Note that the generated filters will not overwrite filters
         declared on the FilterSet.

         Example:
            class UserFilter(FilterSetES):
                username = StringFieldES(field_name='username', lookup_expressions=['contains'])
                class Meta:
                    index = UserIndex
                    includes = {
                            'username': {
                                'lookup_expressions': ['term', 'contains']
                            }

        A query with username as a parameter, will match those words with the
        username value as substring

        The excludes option accept a list of field names.

        Example:
             class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    excludes = ['username', 'last_login']

        It is necessary to provide includes or excludes. You cant provide a excludes empty to generate all fields

        You can also pass sort_by to Meta to allow field be ordered

        Example:
             class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    excludes = []
                    order_by = ['username', 'last_login']

            or

            class UserFilter(FilterSetES):
                class Meta:
                    index = UserIndex
                    excludes = []
                    order_by = {
                            'username': user.name
                            'last_login': last_login
                            }

        """
        self.index = getattr(options, "index", None)
        self.includes = getattr(options, "includes", None)
        self.excludes = getattr(options, "excludes", None)
        self.order_by = getattr(options, "order_by", None)

        if self.index is None:
            raise ValueError("You need provide a Index in Meta.")
        if self.excludes is None and self.includes is None:
            raise ValueError("You need provide includes or excludes field in Meta.")

        self.model = self.index._doc_type.model if self.index else None


class FilterSetESMetaclass(type):
    """Captures the meta class of the filterSet class."""

    def __new__(mcs, name, bases, attrs):
        """Get filters declared explicitly in the class"""
        # get declared as field
        declared_filters = mcs.get_declared_filters(bases, attrs)
        attrs["declared_filters"] = declared_filters

        new_class = super(FilterSetESMetaclass, mcs).__new__(mcs, name, bases, attrs)

        if issubclass(new_class, BaseFilterSet):
            new_class._meta = FilterSetESOptions(getattr(new_class, "Meta", None))

            # get declared as meta
            meta_filters = mcs.get_meta_filters(new_class._meta)

            declared_filters.update(meta_filters)

            # recollecting registered graphene fields and attaching to observable
            base_filters = OrderedDict()
            observable = FieldResolverObservable()
            for filter_name, filter_field in six.iteritems(declared_filters):
                base_filters.update(filter_field.fields)
                filter_field.attach_processor(observable)

            # adding sort field
            sort_fields = {}
            if new_class._meta.order_by is not None:
                sort_fields = mcs.generate_sort_field(new_class._meta.order_by)
                sort_type = mcs.create_sort_enum(name, sort_fields)
                base_filters["sort"] = sort_type()

            new_class.sort_fields = sort_fields
            new_class.base_filters = base_filters
            new_class.observable = observable

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
            (obj.field_name, attrs.pop(filter_name))
            for filter_name, obj in list(attrs.items())
            if isinstance(obj, FilterES)
        ]

        # Merge declared filters from base classes
        for base in reversed(bases):
            if hasattr(base, "declared_filters"):
                filters = [
                    (name, field)
                    for name, field in base.declared_filters.items()
                    if name not in attrs
                ] + filters

        return OrderedDict(filters)

    @classmethod
    def get_meta_filters(mcs, meta):
        """
        Get filters from Meta configuration
        :param meta: A FilterSetESOptions instance with meta options
        :return: Field extracted from index and from the FilterSetES.
        """
        index_fields = mcs.get_index_fields(meta)

        meta_filters = OrderedDict()
        for name, index_field, data in index_fields:
            if isinstance(index_field, ObjectField):
                filters_class = mcs.get_filter_object(name, index_field, data)
                meta_filters.update(filters_class)
            else:
                filter_class = mcs.get_filter_exp(name, index_field, data)
                meta_filters.update({name: filter_class})

        return meta_filters

    @classmethod
    def get_index_fields(mcs, meta):
        """
        Get fields from index that appears in the meta class configuration of the filter_set
        :param meta: A FilterSetESOptions instance with meta options
        :return: Tuple of (name, field, lookup_expr) describing name of the field, ES class of the field and lookup_expr
        """
        index_fields = meta.index._doc_type._fields()
        meta_includes = meta.includes
        meta_excludes = meta.excludes

        if isinstance(meta_includes, dict):
            # The lookup_expr are defined in Meta
            filter_fields = [
                (name, index_fields[name], data) for name, data in meta_includes.items()
            ]
        elif meta_includes is not None:
            # The lookup_expr are not defined
            filter_fields = [(name, index_fields[name], None) for name in meta_includes]
        else:
            # No `includes` are declared in meta, so all not `excludes` fields from index will be converted to filters
            filter_fields = [
                (name, field, None)
                for name, field in index_fields.items()
                if name not in meta_excludes
            ]
        return filter_fields

    @classmethod
    def get_filter_object(mcs, name, field, data):
        """
        Get filters from ObjectField
        :param name: name of the field
        :param field: ES index field
        :param data: lookup_expr
        """
        index_fields = OrderedDict()

        properties = field._doc_class._doc_type.mapping.properties._params.get(
            "properties", {}
        )

        for inner_name, inner_field in properties.items():

            if data and inner_name not in data:
                # This inner field is not filterable
                continue

            inner_data = data[inner_name] if data else None

            filter_exp = mcs.get_filter_exp(
                inner_name, inner_field, inner_data, root=name
            )
            index_fields.update({inner_name: filter_exp})

        return index_fields

    @classmethod
    def get_filter_exp(mcs, name, field, data=None, root=None):
        """
        Initialize filter
        :param name: name of the field
        :param field: ES index field
        :param data: lookup_expr
        :param root: root name
        """
        field_data = try_dbfield(FILTER_FOR_ESFIELD_DEFAULTS.get, field.__class__) or {}
        filter_class = field_data.get("filter_class")

        kwargs = copy.deepcopy(data) if data is not None else {}

        kwargs["field_name"], kwargs["field_name_es"] = mcs.get_name(name, root, data)

        return filter_class(**kwargs)

    @staticmethod
    def get_name(name, root, data):
        """
        Get names of the field and the path to resolve it
        :param name: name of the field
        :param data: lookup_expr
        :param root: root name
        """
        field_name = data.get("field_name", None) if data else None
        field_name_es = data.get("field_name_es", None) if data else None
        if not field_name:
            field_name = "{root}_{name}".format(root=root, name=name) if root else name
        if not field_name_es:
            field_name_es = (
                "{root}.{name}".format(root=root, name=name) if root else name
            )
        return field_name, field_name_es

    @staticmethod
    def create_sort_enum(name, sort_fields):
        """
        Create enum to sort by fields.
        As graphene is typed, it is necessary generate a Enum by Field
        to have inside, the document fields allowed to be ordered
        :param name: name of the field
        :param sort_fields: Field allowed to be ordered
        """

        sort_enum_name = "{}SortFields".format(name)
        sort_descriptions = {
            field: "Sort by {field}".format(field=field) for field in sort_fields.keys()
        }
        sort_fields = [(field, field) for field in sort_fields.keys()]

        class EnumWithDescriptionsType(object):
            """Set description to enum fields"""

            @property
            def description(self):
                """Description to EnumSort"""
                return sort_descriptions[self.name]

        enum = Enum(sort_enum_name, sort_fields, type=EnumWithDescriptionsType)

        class SortType(InputObjectType):
            """Sort Type"""

            order = Field(OrderEnum)
            field = Field(enum, required=True)

        sort_name = "{}Sort".format(name)
        sort_type = type(sort_name, (SortType,), {})
        return sort_type

    @staticmethod
    def generate_sort_field(order_by):
        """
        To normalize the sort field data
        :param order_by: Sort data
        """
        if isinstance(order_by, dict):
            sort_fields = order_by.copy()
        else:
            sort_fields = {field: field for field in order_by}
        return sort_fields


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
        query_base = self.generate_es_query()
        self.es_query.apply_query("query", query_base)
        self.es_query.apply_query("source", ["id"])

        if "sort" in self.data:
            sort_data = self.data["sort"].copy()
            field_name = self.sort_fields[sort_data.pop("field")]
            self.es_query.apply_query("sort", {field_name: sort_data})

        return self.es_query

    def generate_es_query(self):
        """
        Generate a query for each filter.
        :return: Generates a super query with bool as root, and combines all sub-queries from each argument.
        """
        query_base = Q("bool")
        # if the query have data
        if len(self.data):
            # for each field passed to the query
            for name, value in six.iteritems(self.data):
                # ignore sort field
                if name == "sort":
                    continue

                # dispatch observable resolve
                resolve = self.observable.resolve(name, value)
                query_base += resolve

        return query_base
