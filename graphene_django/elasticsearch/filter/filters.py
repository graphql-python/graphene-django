"""Filters to ElasticSearch"""
from collections import OrderedDict
from elasticsearch_dsl import Q
from graphene import String


class StringFilterES(object):  # pylint: disable=R0902
    """String Fields specific to ElasticSearch."""

    default_expr = 'contain'
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
        self.argument = String().Argument()
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
            fields[variant_name] = self

        return fields

    def get_q(self, arguments):
        """
        :param arguments: parameters of the query.
        :return: Returns a elasticsearch_dsl.Q query object.
        """
        queries = []

        for argument, value in arguments.iteritems():
            if argument in self.fields:

                if argument == self.field_name:
                    suffix_expr = self.default_expr or 'default'
                else:
                    argument_split = argument.split("_")
                    suffix_expr = argument_split[len(argument_split) - 1]

                if suffix_expr in self.variants:
                    query = self.variants.get(suffix_expr, None)

                    if query:
                        queries.extend([query(self.field_name, value)])

        return Q("bool", must=queries[0]) if len(queries) == 1 else Q("bool", must={"bool": {"should": queries}})
