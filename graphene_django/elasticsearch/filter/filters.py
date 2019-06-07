"""Filters to ElasticSearch"""
from graphene import String, Boolean, Int
from graphene_django.elasticsearch.filter.processors import PROCESSORS


class FilterES(object):
    """Fields specific to ElasticSearch."""
    default_processor = 'term'
    default_argument = String()

    def __init__(self, field_name, field_name_es=None, lookup_expressions=None,
                 default_processor=None, argument=None):
        """
        :param field_name: Name of the field. This is the name that will be exported.
        :param field_name_es: Path to the index attr that will be used as filter.
        :param lookup_expressions: List of processor.
        :param default_processor: Processor by default used when lookup_expressions in empty.
        :param argument: Gaphene type base for this field.
        """
        self.field_name = field_name

        if isinstance(field_name_es, list):
            self.field_name_es = field_name_es
        else:
            self.field_name_es = [field_name_es or field_name]

        self.default_filter_processor = default_processor or self.default_processor

        self.lookup_expressions = lookup_expressions

        self.processor = None
        if self.lookup_expressions:
            for variant in self.lookup_expressions:
                if variant in PROCESSORS:
                    self.processor = self.build_processor(variant)
                else:
                    raise ValueError('We do not have processor: %s.' % variant)

        else:
            self.processor = self.build_processor(self.default_processor)

        self.argument = argument or self.default_argument
        self.fields = self.processor.generate_field()

    def build_processor(self, variant):
        """
        Create a new processor based on the name
        :param variant: Processor name
        :return: Returns a Processor instance
        """
        processor_class = PROCESSORS[variant]
        return processor_class(self, self.processor)

    def generate_es_query(self, arguments):
        """
        Generating a query based on the arguments passed to graphene field
        :param arguments: parameters of the query.
        :return: Returns a elasticsearch_dsl.Q query object.
        """
        return self.processor.generate_es_query(arguments)


class StringFilterES(FilterES):
    """String Fields specific to ElasticSearch."""
    default_processor = 'contains'


class BoolFilterES(FilterES):
    """Boolean filter to ES"""
    default_argument = Boolean()


class NumberFilterES(FilterES):
    """Filter to an numeric value to ES"""
    default_argument = Int()
