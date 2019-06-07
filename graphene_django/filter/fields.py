from collections import OrderedDict
from functools import partial

from graphene.types.argument import to_arguments
from ..fields import DjangoConnectionField
from .utils import get_filterset_class, get_filtering_args_from_filterset, \
    make_qs

from ..utils import is_parent_set, set_parent


class DjangoFilterConnectionField(DjangoConnectionField):
    def __init__(
        self,
        type,
        fields=None,
        order_by=None,
        extra_filter_meta=None,
        filterset_class=None,
        post_resolver=None,
        *args,
        **kwargs
    ):
        self._fields = fields
        self._provided_filterset_class = filterset_class
        self._filterset_class = None
        self._extra_filter_meta = extra_filter_meta
        self._base_args = None
        self._post_resolver = post_resolver
        self._custom_resolver = kwargs.pop('custom_resolver', False)
        super(DjangoFilterConnectionField, self).__init__(type, *args, **kwargs)

    @property
    def filterset_class(self):
        if not self._filterset_class:
            if hasattr(self.node_type._meta, 'neomodel_filter_fields'):
                fields = self.node_type._meta.neomodel_filter_fields
            elif hasattr(self, '_fields'):
                fields = self._fields
            else:
                fields = []
            meta = dict(model=self.model, fields=fields)
            if self._extra_filter_meta:
                meta.update(self._extra_filter_meta)

            self._filterset_class = get_filterset_class(
                self._provided_filterset_class, **meta
            )
        return self._filterset_class

    @property
    def args(self):
        return to_arguments(self._base_args or OrderedDict(), self.filtering_args)

    @args.setter
    def args(self, args):
        self._base_args = args

    @property
    def filtering_args(self):
        return get_filtering_args_from_filterset(self.filterset_class, self.node_type)

    @classmethod
    def merge_querysets(cls, default_queryset, queryset):
        # There could be the case where the default queryset (returned from the filterclass)
        # and the resolver queryset have some limits on it.
        # We only would be able to apply one of those, but not both
        # at the same time.

        # See related PR: https://github.com/graphql-python/graphene-django/pull/126

        assert not (
            default_queryset.query.low_mark and queryset.query.low_mark
        ), "Received two sliced querysets (low mark) in the connection, please slice only in one."
        assert not (
            default_queryset.query.high_mark and queryset.query.high_mark
        ), "Received two sliced querysets (high mark) in the connection, please slice only in one."
        low = default_queryset.query.low_mark or queryset.query.low_mark
        high = default_queryset.query.high_mark or queryset.query.high_mark
        default_queryset.query.clear_limits()
        queryset = super(DjangoFilterConnectionField, cls).merge_querysets(
            default_queryset, queryset
        )
        queryset.query.set_limits(low, high)
        return queryset

    def get_resolver(self, parent_resolver):
        return partial(
            self.connection_resolver,
            parent_resolver,
            self.type,
            self.get_manager(),
            self.max_limit,
            self.enforce_first_or_last,
            self.filterset_class,
            self.filtering_args,
            self._post_resolver,
            self._custom_resolver,
        )

    @classmethod
    def connection_resolver(cls,
                            resolver,
                            connection,
                            default_manager,
                            max_limit,
                            enforce_first_or_last,
                            filterset_class,
                            filtering_args,
                            post_resolver,
                            custom_resolver,
                            root,
                            info,
                            **args):

        order = args.get('order', None)

        _parent = is_parent_set(info)

        if not _parent:
            _parent = args.get('know_parent', False)

        source_class = default_manager.source

        def new_resolver(root, info, **args):
            # filters
            filters = dict(filter(lambda x: '__' in x[0], args.items()))
            qs = resolver(root, info, **args)
            if qs is None:
                qs = source_class.nodes.filter()

            if filters:
                base_filters, relationship_filters = make_qs(filters)
                qs = qs.filter().filter(base_filters)

                # has filtering
                if relationship_filters:
                    rels = {}
                    # check that this field has relationship in model class
                    for item in relationship_filters.items():
                        rel_field = getattr(source_class, item[0], None)
                        if rel_field is None:
                            raise Exception('This relationship field not found '
                                    'in source class: {class_}'.format(class_=source_class.__name__))
                        # build definition of node_class - source_class( which
                        # must filter by uid - node_class.nodes.get(uid=item[1]))
                        node_class=rel_field.build_manager(0, item[0]).definition['node_class']
                        rels[item[0]]=node_class.nodes.get(uid=item[1])
                    for item in rels.items():
                        qs=qs.has(**{item[0]: item[1]})

            if post_resolver:
                qs = post_resolver(qs, info, **args)

            if order:
                qs=qs.order_by(order)

            # set parent to child fields
            # in ''_parent'' attribute
            if _parent and root is not None:
                return list(map(lambda instance: set_parent(instance, root), qs))
            return qs

        if custom_resolver:
            new_resolver = resolver

        return DjangoConnectionField.connection_resolver(
            new_resolver,
            connection,
            default_manager,
            max_limit,
            enforce_first_or_last,
            root,
            info,
            **args)
