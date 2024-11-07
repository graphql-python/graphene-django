from django_filters.constants import EMPTY_VALUES

from .typed_filter import TypedFilter


class ArrayFilter(TypedFilter):
    """
    Filter made for PostgreSQL ArrayField.
    """

    def filter(self, qs, value):
        """
        Override the default filter class to check first whether the list is
        empty or not.
        This needs to be done as in this case we expect to get the filter applied with
        an empty list since it's a valid value but django_filter consider an empty list
        to be an empty input value (see `EMPTY_VALUES`) meaning that
        the filter does not need to be applied (hence returning the original
        queryset).
        """
        if value in EMPTY_VALUES and value != []:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = "%s__%s" % (self.field_name, self.lookup_expr)
        qs = self.get_method(qs)(**{lookup: value})
        return qs
