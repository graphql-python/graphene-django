from collections import OrderedDict
from functools import partial

from graphene.types.argument import to_arguments
from ..fields import DjangoConnectionField
from .utils import get_filtering_args_from_filterset, get_filterset_class


class DjangoFilterConnectionField(DjangoConnectionField):
    def __init__(
        self,
        type,
        fields=None,
        order_by=None,
        extra_filter_meta=None,
        filterset_class=None,
        *args,
        **kwargs
    ):
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
            meta = dict(model=self.model, fields=fields)
            if self._extra_filter_meta:
                meta.update(self._extra_filter_meta)

            filterset_class = self._provided_filterset_class or (
                self.node_type._meta.filterset_class
            )
            self._filterset_class = get_filterset_class(filterset_class, **meta)

        return self._filterset_class

    @property
    def filtering_args(self):
        return get_filtering_args_from_filterset(self.filterset_class, self.node_type)

    @classmethod
    def resolve_queryset(
        cls, connection, iterable, info, args, filtering_args, filterset_class
    ):
        qs = super(DjangoFilterConnectionField, cls).resolve_queryset(
            connection, iterable, info, args
        )
        filter_kwargs = {k: v for k, v in args.items() if k in filtering_args}
        return filterset_class(data=filter_kwargs, queryset=qs, request=info.context).qs

    def get_queryset_resolver(self):
        return partial(
            self.resolve_queryset,
            filterset_class=self.filterset_class,
            filtering_args=self.filtering_args,
        )
