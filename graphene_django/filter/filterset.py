import itertools

from django.db import models
from django_filters import Filter, MultipleChoiceFilter
from django_filters.filterset import BaseFilterSet, FilterSet
from django_filters.filterset import FILTER_FOR_DBFIELD_DEFAULTS

from graphql_relay.node.node import from_global_id

from ..forms import GlobalIDFormField, GlobalIDMultipleChoiceField


class GlobalIDFilter(Filter):
    field_class = GlobalIDFormField

    def filter(self, qs, value):
        """ Convert the filter value to a primary key before filtering """
        _id = None
        if value is not None:
            _, _id = from_global_id(value)
        return super(GlobalIDFilter, self).filter(qs, _id)


class GlobalIDMultipleChoiceFilter(MultipleChoiceFilter):
    field_class = GlobalIDMultipleChoiceField

    def filter(self, qs, value):
        gids = [from_global_id(v)[1] for v in value]
        return super(GlobalIDMultipleChoiceFilter, self).filter(qs, gids)


GRAPHENE_FILTER_SET_OVERRIDES = {
    models.AutoField: {"filter_class": GlobalIDFilter},
    models.OneToOneField: {"filter_class": GlobalIDFilter},
    models.ForeignKey: {"filter_class": GlobalIDFilter},
    models.ManyToManyField: {"filter_class": GlobalIDMultipleChoiceFilter},
    models.ManyToOneRel: {"filter_class": GlobalIDMultipleChoiceFilter},
    models.ManyToManyRel: {"filter_class": GlobalIDMultipleChoiceFilter},
}


class GrapheneFilterSetMixin(BaseFilterSet):
    """ A django_filters.filterset.BaseFilterSet with default filter overrides
    to handle global IDs """

    FILTER_DEFAULTS = dict(
        itertools.chain(
            FILTER_FOR_DBFIELD_DEFAULTS.items(), GRAPHENE_FILTER_SET_OVERRIDES.items()
        )
    )


def setup_filterset(filterset_class):
    """ Wrap a provided filterset in Graphene-specific functionality
    """
    return type(
        "Graphene{}".format(filterset_class.__name__),
        (filterset_class, GrapheneFilterSetMixin),
        {},
    )


def custom_filterset_factory(model, filterset_base_class=FilterSet, **meta):
    """ Create a filterset for the given model using the provided meta data
    """
    meta.update({"model": model})
    meta_class = type(str("Meta"), (object,), meta)
    filterset = type(
        str("%sFilterSet" % model._meta.object_name),
        (filterset_base_class, GrapheneFilterSetMixin),
        {"Meta": meta_class},
    )
    return filterset
