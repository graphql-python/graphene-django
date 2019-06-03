from elasticsearch_dsl.query import Query
from graphene_django.elasticsearch.filter.bridges import QuerysetBridge
from graphene_django.filter import DjangoFilterConnectionField


class DjangoESFilterConnectionField(DjangoFilterConnectionField):
    """A Field to replace DjangoFilterConnectionField manager by QuerysetBridge"""

    def get_manager(self):
        """Returning a QuerysetBridge to replace the direct use over the QS"""
        return QuerysetBridge(search=self.filterset_class._meta.index.search())

    def merge_querysets(cls, default_queryset, queryset):
        """Merge ES queries"""
        if isinstance(default_queryset, Query):
            return default_queryset & queryset
        return default_queryset.query(queryset)
