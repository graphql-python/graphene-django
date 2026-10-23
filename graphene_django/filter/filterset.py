import itertools

from django.db import models
from django_filters.filterset import (
    FILTER_FOR_DBFIELD_DEFAULTS,
    BaseFilterSet,
    FilterSet,
)

from .filters import GlobalIDFilter, GlobalIDMultipleChoiceFilter

GRAPHENE_FILTER_SET_OVERRIDES = {
    models.AutoField: {"filter_class": GlobalIDFilter},
    models.OneToOneField: {"filter_class": GlobalIDFilter},
    models.ForeignKey: {"filter_class": GlobalIDFilter},
    models.ManyToManyField: {"filter_class": GlobalIDMultipleChoiceFilter},
    models.ManyToOneRel: {"filter_class": GlobalIDMultipleChoiceFilter},
    models.ManyToManyRel: {"filter_class": GlobalIDMultipleChoiceFilter},
}


class GrapheneFilterSetMixin(BaseFilterSet):
    """A django_filters.filterset.BaseFilterSet with default filter overrides
    to handle global IDs"""

    FILTER_DEFAULTS = dict(
        itertools.chain(
            FILTER_FOR_DBFIELD_DEFAULTS.items(), GRAPHENE_FILTER_SET_OVERRIDES.items()
        )
    )

    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        if hasattr(models, "GeneratedField") and isinstance(
            field, models.GeneratedField
        ):
            output_field = field.output_field.clone()
            output_field.model = getattr(field, "model", None)
            output_field.name = getattr(field, "name", None)
            output_field.null = field.null
            field = output_field
        return super().filter_for_field(field, field_name, lookup_expr=lookup_expr)


def setup_filterset(filterset_class):
    """Wrap a provided filterset in Graphene-specific functionality"""
    return type(
        f"Graphene{filterset_class.__name__}",
        (filterset_class, GrapheneFilterSetMixin),
        {},
    )


def custom_filterset_factory(model, filterset_base_class=FilterSet, **meta):
    """Create a filterset for the given model using the provided meta data"""
    meta.update({"model": model})
    meta_class = type("Meta", (object,), meta)
    filterset = type(
        str("%sFilterSet" % model._meta.object_name),
        (filterset_base_class, GrapheneFilterSetMixin),
        {"Meta": meta_class},
    )
    return filterset
