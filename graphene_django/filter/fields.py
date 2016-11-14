from collections import OrderedDict
from functools import partial

from graphene.types.argument import to_arguments
from ..fields import DjangoConnectionField
from .utils import get_filtering_args_from_filterset, get_filterset_class


class DjangoFilterConnectionField(DjangoConnectionField):

    def __init__(self, type, fields=None, order_by=None,
                 extra_filter_meta=None, filterset_class=None,
                 *args, **kwargs):
        self._order_by = order_by
        self._fields = fields
        self._type = type
        self._filterset_class = filterset_class
        self._extra_filter_meta = extra_filter_meta
        self._base_args = None
        super(DjangoFilterConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def node_type(self):
        if callable(self._type):
            return self._type()
        return self._type

    @property
    def order_by(self):
        return self._order_by or self.node_type._meta.filter_order_by

    @property
    def meta(self):
        meta = dict(model=self.node_type._meta.model,
                    fields=self.fields,
                    order_by=self.order_by)
        if self._extra_filter_meta:
            meta.update(self._extra_filter_meta)
        return meta

    @property
    def fields(self):
        return self._fields or self.node_type._meta.filter_fields

    @property
    def args(self):
        return to_arguments(self._base_args or OrderedDict(), self.filtering_args)

    @args.setter
    def args(self, args):
        self._base_args = args

    @property
    def filterset_class(self):
        return get_filterset_class(self._filterset_class, **self.meta)

    @property
    def filtering_args(self):
        return get_filtering_args_from_filterset(self.filterset_class, self.node_type)

    @staticmethod
    def connection_resolver(resolver, connection, default_manager, filterset_class, filtering_args,
                            root, args, context, info):
        filter_kwargs = {k: v for k, v in args.items() if k in filtering_args}
        order = args.get('order_by', None)
        qs = default_manager.get_queryset()
        if order:
            qs = qs.order_by(order)
        qs = filterset_class(data=filter_kwargs, queryset=qs)

        return DjangoConnectionField.connection_resolver(resolver, connection, qs, root, args, context, info)

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager(),
                       self.filterset_class, self.filtering_args)
