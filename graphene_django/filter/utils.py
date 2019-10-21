import six

from django.db.models.constants import LOOKUP_SEP
from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.related import ForeignObjectRel, RelatedField
from .filterset import custom_filterset_factory, setup_filterset


def get_field_parts_with_expression(model, query_expr):
    """
    Traverses the model with a given query expression,
    returns the found fields along the path and the remaining expression
    """
    parts = query_expr.split(LOOKUP_SEP)
    opts = model._meta
    fields = []

    # walk relationships
    for i, name in enumerate(parts):
        try:
            field = opts.get_field(name)
        except FieldDoesNotExist:
            return fields, LOOKUP_SEP.join(parts[i:])

        fields.append(field)
        if isinstance(field, RelatedField):
            opts = field.remote_field.model._meta
        elif isinstance(field, ForeignObjectRel):
            opts = field.related_model._meta

    return fields, "exact"


def get_filtering_args_from_filterset(filterset_class, type):
    """ Inspect a FilterSet and produce the arguments to pass to
        a Graphene Field. These arguments will be available to
        filter against in the GraphQL
    """
    from ..forms.converter import convert_form_field

    args = {}
    model = filterset_class._meta.model
    for name, filter_field in six.iteritems(filterset_class.base_filters):
        form_field = None

        if name in filterset_class.declared_filters:
            form_field = filter_field.field
        else:
            fields, lookup_expr = get_field_parts_with_expression(model, name)
            assert fields, str((model, name, filterset_class))
            model_field = fields[-1]
            filter_type = lookup_expr

            if filter_type != "isnull" and hasattr(model_field, "formfield"):
                form_field = model_field.formfield(
                    required=filter_field.extra.get("required", False)
                )

        # Fallback to field defined on filter if we can't get it from the
        # model field
        if not form_field:
            form_field = filter_field.field

        field_type = convert_form_field(form_field).Argument()
        field_type.description = filter_field.label
        args[name] = field_type

    return args


def get_filterset_class(filterset_class, **meta):
    """Get the class to be used as the FilterSet"""
    if filterset_class:
        # If were given a FilterSet class, then set it up and
        # return it
        return setup_filterset(filterset_class)
    return custom_filterset_factory(**meta)
