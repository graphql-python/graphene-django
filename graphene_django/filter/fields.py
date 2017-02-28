from functools import partial

from ..fields import DjangoConnectionField
from graphene.relay import is_node
from .utils import get_filtering_args_from_filterset, get_filterset_class


class DjangoFilterConnectionField(DjangoConnectionField):

    def __init__(self, type, fields=None, extra_filter_meta=None,
                 filterset_class=None, *args, **kwargs):

        if is_node(type):
            _fields = type._meta.filter_fields
            _model = type._meta.model
        else:
            # ConnectionFields can also be passed Connections,
            # in which case, we need to use the Node of the connection
            # to get our relevant args.
            _fields = type._meta.node._meta.filter_fields
            _model = type._meta.node._meta.model

        self.fields = fields or _fields
        meta = dict(model=_model, fields=self.fields)
        if extra_filter_meta:
            meta.update(extra_filter_meta)
        self.filterset_class = get_filterset_class(filterset_class, **meta)
        self.filtering_args = get_filtering_args_from_filterset(self.filterset_class, type)
        kwargs.setdefault('args', {})
        kwargs['args'].update(self.filtering_args)
        super(DjangoFilterConnectionField, self).__init__(type, *args, **kwargs)

    @staticmethod
    def connection_resolver(resolver, connection, default_manager, filterset_class, filtering_args,
                            root, args, context, info):
        filter_kwargs = {k: v for k, v in args.items() if k in filtering_args}

        def new_resolver(root, args, context, info):
            qs = resolver(root, args, context, info)
            if qs is None:
                qs = default_manager.get_queryset()
            qs = filterset_class(data=filter_kwargs, queryset=qs).qs
            return qs

        return DjangoConnectionField.connection_resolver(new_resolver, connection, None, root, args, context, info)

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver, parent_resolver, self.type, self.get_manager(),
                       self.filterset_class, self.filtering_args)
