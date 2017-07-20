from collections import namedtuple

try:
    from django.db.models.fields.reverse_related import ForeignObjectRel
except ImportError:
    # Django 1.7 doesn't have the reverse_related distinction
    from django.db.models.fields.related import ForeignObjectRel

from django.db.models import ForeignKey
from graphene.utils.str_converters import to_snake_case

from .registry import get_global_registry
from .utils import get_related_model

REGISTRY = get_global_registry()
SELECT = 'select'
PREFETCH = 'prefetch'
RelatedSelection = namedtuple('RelatedSelection', ['name', 'fetch_type'])


def model_fields_as_dict(model):
    return dict((f.name, f) for f in model._meta.get_fields())


def find_model_selections(ast):
    selections = ast.selection_set.selections

    for selection in selections:
        if selection.name.value == 'edges':
            for sub_selection in selection.selection_set.selections:
                if sub_selection.name.value == 'node':
                    return sub_selection.selection_set.selections

    return selections


def get_related_fetches_for_model(model, graphql_ast):
    model_fields = model_fields_as_dict(model)
    selections = find_model_selections(graphql_ast)

    graphene_obj_type = REGISTRY.get_type_for_model(model)
    optimizations = {}
    if graphene_obj_type and graphene_obj_type._meta.optimizations:
        optimizations = graphene_obj_type._meta.optimizations

    relateds = []

    for selection in selections:
        selection_name = to_snake_case(selection.name.value)
        selection_field = model_fields.get(selection_name, None)

        try:
            related_model = get_related_model(selection_field)
        except:
            # This is not a ForeignKey or Relation, check manual optimizations
            manual_optimizations = optimizations.get(selection_name)
            if manual_optimizations:
                for manual_select in manual_optimizations.get(SELECT, []):
                    relateds.append(RelatedSelection(manual_select, SELECT))
                for manual_prefetch in manual_optimizations.get(PREFETCH, []):
                    relateds.append(RelatedSelection(manual_prefetch, PREFETCH))

            continue

        query_name = selection_field.name
        if isinstance(selection_field, ForeignObjectRel):
            query_name = selection_field.field.related_query_name()

        nested_relateds = get_related_fetches_for_model(related_model, selection)

        related_type = PREFETCH  # default to prefetch, it's safer
        if isinstance(selection_field, ForeignKey):
            related_type = SELECT  # we can only select for ForeignKeys

        if nested_relateds:
            for related in nested_relateds:
                full_name = '{0}__{1}'.format(query_name, related.name)

                nested_related_type = PREFETCH
                if related_type == SELECT and related.fetch_type == SELECT:
                    nested_related_type = related_type

                relateds.append(RelatedSelection(full_name, nested_related_type))
        else:
            relateds.append(RelatedSelection(query_name, related_type))

    return relateds


def optimize_queryset(queryset, graphql_info):
    base_ast = graphql_info.field_asts[0]
    relateds = get_related_fetches_for_model(queryset.model, base_ast)

    for related in relateds:
        if related.fetch_type == SELECT:
            queryset = queryset.select_related(related.name)
        else:
            queryset = queryset.prefetch_related(related.name)

    return queryset
