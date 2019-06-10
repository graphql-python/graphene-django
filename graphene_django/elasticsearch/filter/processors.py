from collections import OrderedDict

from elasticsearch_dsl import Q
from graphene import List, Boolean


class Processor(object):
    suffix_expr = "term"

    def __init__(self, filter_es, parent_processor=None):
        """
        Abstract processor to generate graphene field and ES query to lookups
        :param filter_es: A FilterES target
        :param parent_processor: Next Processor to the generate field chain
        """
        self.filter_es = filter_es
        self.parent_processor = parent_processor
        self.variant_name = self._get_variant_name()

    def generate_field(self):
        """Field Decorator"""
        self_field = self._build_field()

        if self.parent_processor is not None:
            parent_fields = self.parent_processor.generate_field()
            parent_fields.update(self_field)
            return parent_fields

        else:
            return self_field

    def get_type(self):
        """Define the argument for graphene field"""
        return self.filter_es.argument

    def to_attach(self, observer):
        """
        Add this processor to FieldResolverObservable
        :param observer: observer to attach the processors.
        """
        observer.attach(self.variant_name, self)

        if self.parent_processor is not None:
            self.parent_processor.to_attach(observer)

    def _build_field(self):
        """
        Specific detail about field creation to be overwrite if necessary.
        :return: A field
        """
        variant_name = self.variant_name

        return OrderedDict({variant_name: self.get_type()})

    def _get_variant_name(self):
        """
        Make a variant based on filter name and processor suffix
        :return: A variant name
        """
        if self.suffix_expr == self.filter_es.default_filter_processor:
            variant_name = self.filter_es.field_name

        else:
            variant_name = "%s_%s" % (self.filter_es.field_name, self.suffix_expr)

        return variant_name

    def build_query(self, value):
        """
        Make a query based on specific processor query
        :param value: Value passed to this processor
        :return: A elasticsearch Query
        """
        result = len(self.filter_es.field_name_es)

        if result > 1:
            queries = [
                self._get_query(name, value) for name in self.filter_es.field_name_es
            ]
            return Q("bool", must={"bool": {"should": queries}})

        return Q("bool", must=self._get_query(self.filter_es.field_name_es[0], value))

    @staticmethod
    def _get_query(name, value):
        """
        Specific detail about query creation to be overwrite if necessary.
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("term", **{name: value})


class TermProcessor(Processor):
    """Have a same behavior of parent this is only with semantic proposal"""

    pass


class ContainsProcessor(Processor):
    """fuzzy search"""

    suffix_expr = "contains"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("match", **{name: {"query": value, "fuzziness": "auto"}})


class RegexProcessor(Processor):
    """Search based on regular expressions"""

    suffix_expr = "regex"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("wildcard", **{name: value})


class PhraseProcessor(Processor):
    """Search by the union of many terms"""

    suffix_expr = "phrase"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("match_phrase", **{name: {"query": value}})


class PrefixProcessor(Processor):
    """Search by the prefix of the terms"""

    suffix_expr = "prefix"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("match_phrase_prefix", **{name: {"query": value}})


class InProcessor(Processor):
    """Search by many value for a field"""

    suffix_expr = "in"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("terms", **{name: value})

    def get_type(self):
        """Change base argument by a list of base argument"""
        return List(self.filter_es.argument.Argument().type)


class ExitsProcessor(Processor):
    """Search by if the field is in the document"""

    suffix_expr = "exits"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q(
            "bool", **{"must" if value else "must_not": {"exists": {"field": name}}}
        )

    def get_type(self):
        return Boolean()


class LteProcessor(Processor):
    """Search by range less than"""

    suffix_expr = "lte"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("range", **{name: {"lte": value}})


class GteProcessor(Processor):
    """Search by range greater than"""

    suffix_expr = "gte"

    @staticmethod
    def _get_query(name, value):
        """
        Overwrite query creation
        :param name: elasticsearch document field name
        :param value: Value passed to this processor
        :return:  A elasticsearch Query
        """
        return Q("range", **{name: {"gte": value}})


class ProcessorFactory(object):
    processors = {
        "contains": ContainsProcessor,
        "term": TermProcessor,
        "regex": RegexProcessor,
        "phrase": PhraseProcessor,
        "prefix": PrefixProcessor,
        "in": InProcessor,
        "exits": ExitsProcessor,
        "lte": LteProcessor,
        "gte": GteProcessor,
    }

    @classmethod
    def make_processor(cls, variant, filter_es, parent_processor):
        """
        Create a new processor based on the name
        :param variant: Processor name
        :param filter_es: Target filter
        :param parent_processor: Parent in the chain
        :return: Returns a Processor instance
        """
        if variant in cls.processors:
            processor_class = cls.processors[variant]
            return processor_class(filter_es, parent_processor)

        else:
            raise ValueError("We do not have processor: %s." % variant)
