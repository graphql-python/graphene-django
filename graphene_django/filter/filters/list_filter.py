from .typed_filter import TypedFilter


class ListFilter(TypedFilter):
    """
    Filter that takes a list of value as input.
    It is for example used for `__in` filters.
    """

    def filter(self, qs, value):
        """
        Override the default filter class to check first whether the list is
        empty or not.
        This needs to be done as in this case we expect to get an empty output
        (if not an exclude filter) but django_filter consider an empty list
        to be an empty input value (see `EMPTY_VALUES`) meaning that
        the filter does not need to be applied (hence returning the original
        queryset).
        """
        if value is not None and len(value) == 0:
            if self.exclude:
                return qs
            else:
                return qs.none()
        else:
            return super(ListFilter, self).filter(qs, value)
