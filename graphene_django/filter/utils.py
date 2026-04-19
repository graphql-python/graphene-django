from django import forms
from django_filters.utils import get_model_field

import graphene

from ..forms import GlobalIDFormField, GlobalIDMultipleChoiceField
from .filters import ListFilter, RangeFilter, TypedFilter
from .filterset import custom_filterset_factory, setup_filterset


def get_field_type_from_registry(registry, model, field_name):
    """Resolve the GraphQL type for ``model.field_name`` from the registry.

    Looks up the ``DjangoObjectType`` registered for ``model`` and returns
    the GraphQL type associated with ``field_name`` on it, unwrapping a
    ``NonNull`` wrapper when present so callers always receive the underlying
    named type.

    Returns ``None`` when either the model is not registered as a
    ``DjangoObjectType`` or the type does not expose ``field_name``. A
    ``None`` return is the caller's signal to fall back to converting the
    Django form field instead.
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


def _is_foreign_key_form_field(form_field):
    """Return ``True`` when ``form_field`` represents a foreign-key relation.

    Foreign-key form fields are routed through the related model's ``id`` in
    :func:`_get_field_type_from_model_field` because filtering on a relation
    in GraphQL means filtering on the related node's identifier rather than
    on the relation column itself.
    """
    return isinstance(
        form_field,
        (
            forms.ModelChoiceField,
            forms.ModelMultipleChoiceField,
            GlobalIDFormField,
            GlobalIDMultipleChoiceField,
        ),
    )


def _get_field_type_from_model_field(model_field, form_field, registry):
    """Resolve the GraphQL type for ``model_field`` via the registry.

    For foreign-key form fields, lookup is performed on the related model's
    ``id`` (since filtering on a foreign key in GraphQL means filtering on
    the related node identifier). For all other fields, lookup is performed
    on the owning model + the model field name directly.

    Delegates the actual registry lookup to
    :func:`get_field_type_from_registry`.
    """
    if _is_foreign_key_form_field(form_field):
        return get_field_type_from_registry(registry, model_field.related_model, "id")

    return get_field_type_from_registry(registry, model_field.model, model_field.name)


def _get_form_field(model_field, filter_field, required):
    """Resolve which Django form field to use to validate the filter input.

    Resolution order:

    1. The form field corresponding to the model field (``model_field.formfield(required=...)``)
       when the model field exposes a ``formfield`` factory.
    2. The form field declared on the filter itself (``filter_field.field``)
       when the model field's factory yields a falsy value or when the
       model field has no ``formfield`` factory at all.

    ``model_field`` may be ``None`` (when the filter targets something that
    is not a real model field, e.g. an annotation or a method-only filter).
    In that case we always fall through to ``filter_field.field``.
    """
    form_field = None
    if hasattr(model_field, "formfield"):
        form_field = model_field.formfield(required=required)
    if not form_field:
        form_field = filter_field.field
    return form_field


def _get_field_type_and_form_field_for_implicit_filter(
    model, filter_type, filter_field, registry, required
):
    """Resolve the GraphQL type for a filter that is not explicitly declared.

    Implicit filters are those generated from ``Meta.fields = {...}`` on the
    ``FilterSet`` (rather than declared as class attributes). Their type is
    derived from the underlying model field.

    Returns a ``(field_type, form_field)`` tuple where:

    * ``field_type`` is the resolved GraphQL type, or ``None`` if it could
      not be derived from the model — in which case the caller falls back
      to converting the form field via :func:`_get_field_type_for_explicit_filter`.
    * ``form_field`` is the Django form field that the caller may reuse for
      the explicit-filter fallback so it does not need to resolve it twice.

    Special-case: ``isnull`` lookups are always boolean and need no form
    field, so the helper short-circuits with ``(graphene.Boolean, None)``.
    """
    if filter_type == "isnull":
        return graphene.Boolean, None

    model_field = get_model_field(model, filter_field.field_name)
    form_field = _get_form_field(model_field, filter_field, required)

    if model_field:
        field_type = _get_field_type_from_model_field(model_field, form_field, registry)
        return field_type, form_field

    return None, form_field


def _get_field_type_for_explicit_filter(filter_field, form_field):
    """Resolve the GraphQL type for an explicitly-declared filter via form-field conversion.

    Used when:

    * The filter was declared explicitly on the ``FilterSet`` class (so its
      type cannot be derived from a model field), or
    * The implicit-filter path could not resolve a registry type (e.g. the
      target model is not exposed via a ``DjangoObjectType``).

    Falls back to ``filter_field.field`` when ``form_field`` is falsy, then
    runs the form field through :func:`graphene_django.forms.converter.convert_form_field`
    to obtain the final GraphQL type.
    """
    from ..forms.converter import convert_form_field

    form_field = form_field or filter_field.field
    return convert_form_field(form_field).get_type()


def _is_filter_list_or_range(filter_field):
    """Return ``True`` when the filter is a ``ListFilter`` or ``RangeFilter``.

    Both filter classes accept a list of values for the ``in`` and ``range``
    lookups, so their argument type must be wrapped in ``graphene.List``.
    See :func:`replace_csv_filters` for context on why these custom filter
    classes exist.
    """
    return isinstance(filter_field, (ListFilter, RangeFilter))


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
                field_type, form_field = _get_field_type_and_form_field_for_implicit_filter(
                    model, filter_type, filter_field, registry, required
                )

            if not field_type:
                field_type = _get_field_type_for_explicit_filter(
                    filter_field, form_field
                )

            if _is_filter_list_or_range(filter_field):
                # Replace InFilter/RangeFilter filters (`in`, `range`) argument type to be a list of
                # the same type as the field. See comments in `replace_csv_filters` method for more details.
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
    But with GraphQL we can actually have a list as input and have a proper
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
