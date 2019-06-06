from collections import OrderedDict

from elasticsearch_dsl import Q
from graphene import List


class Processor(object):
    suffix_expr = 'term'

    def __init__(self, filter_es, parent_processor=None):
        """
        Abstract processor to generate graphene field and ES query to lookups
        :type filter_es: graphene_django.elasticsearch.filter.filterset.FilterES
        :type parent_processor: graphene_django.elasticsearch.filter.filterset.Processor
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
        return self.filter_es.argument

    def generate_es_query(self, data):

        if self.variant_name in data:
            value = data.get(self.variant_name)
            self_query = self._build_query(value)
        else:
            self_query = Q("bool")

        if self.parent_processor is not None:
            parent_query = self.parent_processor.generate_es_query(data)
            parent_query += self_query
            return parent_query

        else:
            return self_query

    def _build_field(self):
        variant_name = self.variant_name

        return OrderedDict({variant_name: self.filter_es})

    def _get_variant_name(self):
        if self.suffix_expr == self.filter_es.default_filter_processor:
            variant_name = self.filter_es.field_name

        else:
            variant_name = "%s_%s" % (self.filter_es.field_name, self.suffix_expr)

        return variant_name

    def _build_query(self, value):
        result = len(self.filter_es.field_name_es)

        if result > 1:
            queries = [self._get_query(name, value) for name in self.filter_es.field_name_es]
            return Q("bool", must={"bool": {"should": queries}})

        return Q("bool", must=self._get_query(self.filter_es.field_name_es[0], value))

    @staticmethod
    def _get_query(name, value):
        return Q('term', **{name: value})


class TermProcessor(Processor):
    pass


class ContainsProcessor(Processor):
    suffix_expr = 'contains'

    @staticmethod
    def _get_query(name, value):
        return Q('match',
                 **{name: {
                     "query": value,
                     "fuzziness": "auto"
                 }})


class RegexProcessor(Processor):
    suffix_expr = 'regex'

    @staticmethod
    def _get_query(name, value):
        return Q('wildcard', **{name: value})


class PhraseProcessor(Processor):
    suffix_expr = 'phrase'

    @staticmethod
    def _get_query(name, value):
        return Q('match_phrase',
                 **{name: {
                     "query": value
                 }})


class PrefixProcessor(Processor):
    suffix_expr = 'prefix'

    @staticmethod
    def _get_query(name, value):
        return Q('match_phrase_prefix',
                 **{name: {
                     "query": value
                 }})


class InProcessor(Processor):
    suffix_expr = 'in'

    def get_type(self):
        return List(self.filter_es.argument.Argument().type)


class ExitsProcessor(Processor):
    suffix_expr = 'exits'

    @staticmethod
    def _get_query(name, value):
        return Q('bool', **{
            'must' if value else 'must_not': {'exists': {'field': name}}
        })


class LteProcessor(Processor):
    suffix_expr = 'lte'

    @staticmethod
    def _get_query(name, value):
        return Q("bool", must={'range': {name: {'lte': value}}})


class GteProcessor(Processor):
    suffix_expr = 'gte'

    @staticmethod
    def _get_query(name, value):
        return Q("bool", must={'range': {name: {'gte': value}}})


PROCESSORS = {
    "contains": ContainsProcessor,
    "term": TermProcessor,
    "regex": RegexProcessor,
    "phrase": PhraseProcessor,
    "prefix": PrefixProcessor,
    "in": InProcessor,
    "lte": LteProcessor,
    "gte": GteProcessor,
}
