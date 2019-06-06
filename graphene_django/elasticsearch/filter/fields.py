from elasticsearch_dsl.query import Query

from graphene_django.elasticsearch.filter.bridges import ManagerBridge
from graphene_django.filter import DjangoFilterConnectionField


class DjangoESFilterConnectionField(DjangoFilterConnectionField):
    """A Field to replace DjangoFilterConnectionField manager by QuerysetBridge"""
    def __init__(self, object_type, *args, **kwargs):
        """Validating field allowed for this connection"""
        fields = kwargs.get('fields', None)
        if fields is not None:
            raise ValueError('DjangoESFilterConnectionField do not permit argument fields yet.')

        order_by = kwargs.get('order_by', None)
        if order_by is not None:
            raise ValueError('DjangoESFilterConnectionField do not permit argument order_by yet.')

        filterset_class = kwargs.get('filterset_class', None)
        if filterset_class is None:
            raise ValueError('You should provide a FilterSetES as filterset_class argument.')

        super(DjangoESFilterConnectionField, self).__init__(object_type, *args, **kwargs)

        self.manager = ManagerBridge(search_manager=self.filterset_class._meta.index.search)

    def get_manager(self):
        """Returning a ManagerBridge to replace the direct use over the Model manager"""
        return self.manager

    def merge_querysets(cls, default_queryset, queryset):
        """Merge ES queries"""
        if isinstance(default_queryset, Query):
            return default_queryset & queryset
        return default_queryset.query(queryset)
