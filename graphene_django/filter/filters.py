from django.core.exceptions import ValidationError
from django.forms import Field

from django_filters import Filter, MultipleChoiceFilter
from django_filters.constants import EMPTY_VALUES

from graphql_relay.node.node import from_global_id

from ..forms import GlobalIDFormField, GlobalIDMultipleChoiceField


class GlobalIDFilter(Filter):
    """
    Filter for Relay global ID.
    """

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


class ListFilter(Filter):
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
            return super().filter(qs, value)


def validate_range(value):
    """
    Validator for range filter input: the list of value must be of length 2.
    Note that validators are only run if the value is not empty.
    """
    if len(value) != 2:
        raise ValidationError(
            "Invalid range specified: it needs to contain 2 values.", code="invalid"
        )


class RangeField(Field):
    default_validators = [validate_range]
    empty_values = [None]


class RangeFilter(Filter):
    field_class = RangeField


class ArrayFilter(Filter):
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
