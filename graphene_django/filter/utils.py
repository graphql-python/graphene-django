from django import forms
from django_filters.utils import get_model_field

import graphene

from ..forms import GlobalIDFormField, GlobalIDMultipleChoiceField
from .filters import ListFilter, RangeFilter, TypedFilter
from .filterset import custom_filterset_factory, setup_filterset


def get_field_type_from_registry(registry, model, field_name):
    """
    Try to get a model field corresponding GraphQL type from the DjangoObjectType.
    """
    object_type = registry.get_type_for_model(model)
    if not object_type:
        return None

    object_type_field = object_type._meta.fields.get(field_name)
    if not object_type_field:
        return None

    field_type = object_type_field.type
    if isinstance(field_type, graphene.NonNull):
        field_type = field_type.of_type
    return field_type


def get_field_type_from_model_field(model_field, form_field, registry):
    """
    Get the field type from the model field.

    If the model field is a foreign key, then we need to get the type from the related model.
    """
    if (
        isinstance(form_field, forms.ModelChoiceField)
        or isinstance(form_field, forms.ModelMultipleChoiceField)
        or isinstance(form_field, GlobalIDMultipleChoiceField)
        or isinstance(form_field, GlobalIDFormField)
    ):
        # Foreign key have dynamic types and filtering on a foreign key actually means filtering on its ID.
        return get_field_type_from_registry(registry, model_field.related_model, "id")

    return get_field_type_from_registry(registry, model_field.model, model_field.name)


def get_form_field(model_field, filter_field, required):
    """
    Retrieve the form field to use for the filter.

    Get the form field either from:
    #  1. the formfield corresponding to the model field
    #  2. the field defined on filter

    Returns None if no form field can be found.
    """
    form_field = None
    if hasattr(model_field, "formfield"):
        form_field = model_field.formfield(required=required)
    if not form_field:
        form_field = filter_field.field
    return form_field


def get_field_type_and_form_field_for_implicit_filter(
    model, filter_type, filter_field, registry, required
):
    """
    Get the filter type for filters that are not explicitly declared.

    Returns a tuple of (field_type, form_field) where:
    - field_type is the type of the filter argument
    - form_field is the form field to use to validate the input value
    """
    if filter_type == "isnull":
        # Filter type is boolean, no form field.
        return (graphene.Boolean, None)

    model_field = get_model_field(model, filter_field.field_name)
    form_field = get_form_field(model_field, filter_field, required)

    # First try to get the matching field type from the GraphQL DjangoObjectType
    if model_field:
        field_type = get_field_type_from_model_field(model_field, form_field, registry)
        return (field_type, form_field)

    return (None, None)


def get_field_type_for_explicit_filter(filter_field, form_field):
    """
    Fallback on converting the form field either because:
    - it's an explicitly declared filters
    - we did not manage to get the type from the model type
    """
    from ..forms.converter import convert_form_field

    form_field = form_field or filter_field.field
    return convert_form_field(form_field).get_type()


def is_filter_list_or_range(filter_field):
    """
    Determine if the filter is a ListFilter or RangeFilter.
    """
    return isinstance(filter_field, ListFilter) or isinstance(filter_field, RangeFilter)


def get_filtering_args_from_filterset(filterset_class, type):
    """
    Inspect a FilterSet and produce the arguments to pass to a Graphene Field.
    These arguments will be available to filter against in the GraphQL API.
    """

    args = {}
    model = filterset_class._meta.model
    registry = type._meta.registry
    for name, filter_field in filterset_class.base_filters.items():
        filter_type = filter_field.lookup_expr
        required = filter_field.extra.get("required", False)
        field_type = None
        form_field = None

        if (
            isinstance(filter_field, TypedFilter)
            and filter_field.input_type is not None
        ):
            # First check if the filter input type has been explicitly given
            field_type = filter_field.input_type
        else:
            if name not in filterset_class.declared_filters or isinstance(
                filter_field, TypedFilter
            ):
                (
                    field_type,
                    form_field,
                ) = get_field_type_and_form_field_for_implicit_filter(
                    model, filter_type, filter_field, registry, required
                )

            if not field_type:
                field_type = get_field_type_for_explicit_filter(
                    filter_field, form_field
                )

            # Replace InFilter/RangeFilter filters (`in`, `range`) argument type to be a list of
            # the same type as the field. See comments in `replace_csv_filters` method for more details.
            if is_filter_list_or_range(filter_field):
                field_type = graphene.List(field_type)

        args[name] = graphene.Argument(
            field_type,
            description=filter_field.label,
            required=required,
        )

    return args


def get_filterset_class(filterset_class, **meta):
    """
    Get the class to be used as the FilterSet.
    """
    if filterset_class:
        # If were given a FilterSet class, then set it up.
        graphene_filterset_class = setup_filterset(filterset_class)
    else:
        # Otherwise create one.
        graphene_filterset_class = custom_filterset_factory(**meta)

    replace_csv_filters(graphene_filterset_class)
    return graphene_filterset_class


def replace_csv_filters(filterset_class):
    """
    Replace the "in" and "range" filters (that are not explicitly declared)
    to not be BaseCSVFilter (BaseInFilter, BaseRangeFilter) objects anymore
    but our custom InFilter/RangeFilter filter class that use the input
    value as filter argument on the queryset.

    This is because those BaseCSVFilter are expecting a string as input with
    comma separated values.
    But with GraphQl we can actually have a list as input and have a proper
    type verification of each value in the list.

    See issue https://github.com/graphql-python/graphene-django/issues/1068.
    """
    for name, filter_field in list(filterset_class.base_filters.items()):
        # Do not touch any declared filters
        if name in filterset_class.declared_filters:
            continue

        filter_type = filter_field.lookup_expr
        if filter_type == "in":
            filterset_class.base_filters[name] = ListFilter(
                field_name=filter_field.field_name,
                lookup_expr=filter_field.lookup_expr,
                label=filter_field.label,
                method=filter_field.method,
                exclude=filter_field.exclude,
                **filter_field.extra,
            )
        elif filter_type == "range":
            filterset_class.base_filters[name] = RangeFilter(
                field_name=filter_field.field_name,
                lookup_expr=filter_field.lookup_expr,
                label=filter_field.label,
                method=filter_field.method,
                exclude=filter_field.exclude,
                **filter_field.extra,
            )
