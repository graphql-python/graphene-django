"""Filters to ElasticSearch"""
from collections import OrderedDict
from django_filters import CharFilter
from elasticsearch_dsl import Q


class StringFilterES(object):  # pylint: disable=R0902
    """String Fields specific to ElasticSearch."""

    default_expr = 'contain'
    filter_class = CharFilter

    variants = {
        "contain": lambda name, value: Q('match',
                                         **{name: {
                                             "query": value,
                                             "fuzziness": "auto"
                                         }}),

        "term": lambda name, value: Q('term', **{name: value}),
    }

    def __init__(self, name=None, attr=None):
        """
        :param name: Name of the field. This is the name that will be exported.
        :param attr: Path to the index attr that will be used as filter.
        """
        assert name or attr, "At least the field name or the field attr should be passed"
        self.field_name = name or attr.replace('.', '_')
        self.fields = self.generate_fields()

    def generate_fields(self):
        """
        All FilterSet objects should specify its fields for the introspection.

        :return: A mapping of field to Filter type of field with all the suffix
            expressions combinations.
        """
        fields = OrderedDict()
        for variant in self.variants:
            variant_name = self.field_name if variant in ["default", self.default_expr] \
                else "%s_%s" % (self.field_name, variant)
            fields[variant_name] = self.filter_class(field_name=variant_name)

        return fields
