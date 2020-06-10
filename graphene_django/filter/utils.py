from django_filters.utils import get_model_field
from .filterset import custom_filterset_factory, setup_filterset


def get_filtering_args_from_filterset(filterset_class, type):
    """ Inspect a FilterSet and produce the arguments to pass to
        a Graphene Field. These arguments will be available to
        filter against in the GraphQL
    """
    from ..forms.converter import convert_form_field

    args = {}
    model = filterset_class._meta.model
    for name, filter_field in filterset_class.base_filters.items():
        form_field = None

        if name in filterset_class.declared_filters:
            form_field = filter_field.field
        else:
            model_field = get_model_field(model, filter_field.field_name)
            filter_type = filter_field.lookup_expr
            if filter_type != "isnull" and hasattr(model_field, "formfield"):
                form_field = model_field.formfield(
                    required=filter_field.extra.get("required", False)
                )

        # Fallback to field defined on filter if we can't get it from the
        # model field
        if not form_field:
            form_field = filter_field.field

        field_type = convert_form_field(form_field).Argument()
        field_type.description = str(filter_field.label) if filter_field.label else None
        args[name] = field_type

    return args


def get_filterset_class(filterset_class, **meta):
    """Get the class to be used as the FilterSet"""
    if filterset_class:
        # If were given a FilterSet class, then set it up and
        # return it
        return setup_filterset(filterset_class)
    return custom_filterset_factory(**meta)
