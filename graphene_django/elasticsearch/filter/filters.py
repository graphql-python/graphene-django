"""Filters to ElasticSearch"""
from graphene import String, Boolean, Int
from graphene_django.elasticsearch.filter.processors import ProcessorFactory


class FilterES(object):
    """Fields specific to ElasticSearch."""

    default_processor = "term"
    default_argument = String()

    def __init__(
        self,
        field_name,
        field_name_es=None,
        lookup_expressions=None,
        default_processor=None,
        argument=None,
    ):
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
                self.processor = ProcessorFactory.make_processor(
                    variant, self, self.processor
                )

        else:
            self.processor = ProcessorFactory.make_processor(
                self.default_processor, self, self.processor
            )

        self.argument = argument or self.default_argument
        self.fields = self.processor.generate_field()

    def attach_processor(self, observer):
        """
        Generating a query based on the arguments passed to graphene field
        :param observer: observer to attach the processors.
        """
        return self.processor.to_attach(observer)


class StringFilterES(FilterES):
    """String Fields specific to ElasticSearch."""

    default_processor = "contains"


class BoolFilterES(FilterES):
    """Boolean filter to ES"""

    default_argument = Boolean()


class NumberFilterES(FilterES):
    """Filter to an numeric value to ES"""

    default_argument = Int()
