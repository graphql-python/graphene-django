from collections import OrderedDict
from functools import partial

# from graphene.relay import is_node
from graphene.types.argument import to_arguments
from ..fields import DjangoConnectionField
from .utils import get_filtering_args_from_filterset, get_filterset_class


class DjangoFilterConnectionField(DjangoConnectionField):

    def __init__(self, type, fields=None, order_by=None,
                 extra_filter_meta=None, filterset_class=None,
                 *args, **kwargs):
        self._fields = fields
        self._provided_filterset_class = filterset_class
        self._filterset_class = None
        self._extra_filter_meta = extra_filter_meta
        self._base_args = None
        super(DjangoFilterConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def args(self):
        return to_arguments(self._base_args or OrderedDict(), self.filtering_args)

    @args.setter
    def args(self, args):
        self._base_args = args

    @property
    def filterset_class(self):
        if not self._filterset_class:
            fields = self._fields or self.node_type._meta.filter_fields
            meta = dict(model=self.model,
                        fields=fields)
            if self._extra_filter_meta:
                meta.update(self._extra_filter_meta)

            self._filterset_class = get_filterset_class(self._provided_filterset_class, **meta)

        return self._filterset_class

    @property
    def filtering_args(self):
        return get_filtering_args_from_filterset(self.filterset_class, self.node_type)

    @staticmethod
    def connection_resolver(resolver, connection, default_manager, filterset_class, filtering_args,
                            root, args, context, info):
        filter_kwargs = {k: v for k, v in args.items() if k in filtering_args}
        qs = filterset_class(
            data=filter_kwargs,
            queryset=default_manager.get_queryset()
        ).qs
        return DjangoConnectionField.connection_resolver(resolver, connection, qs, root, args, context, info)

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager(),
                       self.filterset_class, self.filtering_args)
