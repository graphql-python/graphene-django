import six

from .filterset import custom_filterset_factory, setup_filterset


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
            try:
                field_name, filter_type = name.rsplit("__", 1)
            except ValueError:
                field_name = name
                filter_type = None

            # If the filter type is `isnull` then use the filter provided by
            # DjangoFilter (a BooleanFilter).
            # Otherwise try and get a filter based on the actual model field
            if filter_type != "isnull" and hasattr(model, field_name):
                model_field = model._meta.get_field(field_name)

                if hasattr(model_field, "formfield"):
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
