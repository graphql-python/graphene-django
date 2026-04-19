"""Focused unit tests for the filter-type resolution helpers.

These tests cover the helpers extracted from
:func:`graphene_django.filter.utils.get_filtering_args_from_filterset`:

* :func:`get_field_type_from_registry`
* :func:`_is_foreign_key_form_field`
* :func:`_get_field_type_from_model_field`
* :func:`_get_form_field`
* :func:`_get_field_type_and_form_field_for_implicit_filter`
* :func:`_get_field_type_for_explicit_filter`
* :func:`_is_filter_list_or_range`

Each helper has at least one test per documented branch so that a
regression in any single branch fails a focused test rather than only
being detected via the integration-level ``test_fields.py`` suite.

The file also pins one **integration** scenario that exercises the
``get_filtering_args_from_filterset`` flow end-to-end for the
"non-model field" path — this protects against the subtle behavioural
parity concern flagged in the PR review (the implicit-filter helper
must still allow the explicit-filter fallback to take over when the
filter targets something that is not a real model field).

Assumptions that apply to the file as a whole:

* ``django-filter`` is installed (the whole module is skipped via
  ``pytestmark`` otherwise, matching the convention used in the rest of
  ``graphene_django/filter/tests``).
* The shared :class:`graphene_django.tests.models.Pet` /
  :class:`graphene_django.tests.models.Person` /
  :class:`graphene_django.tests.models.Reporter` models are available
  for use in test fixtures.
"""

import pytest
from django import forms
from django_filters import CharFilter, FilterSet, NumberFilter

import graphene
from graphene import NonNull

from graphene_django import DjangoObjectType
from graphene_django.forms import GlobalIDFormField, GlobalIDMultipleChoiceField
from graphene_django.registry import Registry
from graphene_django.tests.models import Person, Pet, Reporter
from graphene_django.utils import DJANGO_FILTER_INSTALLED

from ..filters import ListFilter, RangeFilter
from ..utils import (
    _get_field_type_and_form_field_for_implicit_filter,
    _get_field_type_for_explicit_filter,
    _get_field_type_from_model_field,
    _get_form_field,
    _is_filter_list_or_range,
    _is_foreign_key_form_field,
    get_field_type_from_registry,
    get_filtering_args_from_filterset,
)

pytestmark = []
if not DJANGO_FILTER_INSTALLED:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )


@pytest.fixture
def isolated_registry():
    """A fresh :class:`Registry` that does not pollute the global one."""
    return Registry()


@pytest.fixture
def reporter_type(isolated_registry):
    """A :class:`DjangoObjectType` for Reporter registered in the isolated registry.

    Used by the ``get_field_type_from_registry`` tests to assert that the
    helper correctly looks up the Graphene type for a given model + field
    combination. Returns the type class.
    """

    class ReporterFilterType(DjangoObjectType):
        class Meta:
            model = Reporter
            fields = "__all__"
            registry = isolated_registry

    return ReporterFilterType


@pytest.fixture
def pet_type(isolated_registry):
    """A :class:`DjangoObjectType` for Pet registered in the isolated registry.

    Pet has a foreign key (``owner``) to Person, used by the FK-routing
    branch tests of :func:`_get_field_type_from_model_field`.
    """

    class PetFilterType(DjangoObjectType):
        class Meta:
            model = Pet
            fields = "__all__"
            registry = isolated_registry

    return PetFilterType


@pytest.fixture
def person_type(isolated_registry):
    """A :class:`DjangoObjectType` for Person registered in the isolated registry.

    Required so the FK-routing branch can resolve ``Person.id`` via the
    registry when the related model is queried for its ``id`` field.
    """

    class PersonFilterType(DjangoObjectType):
        class Meta:
            model = Person
            fields = "__all__"
            registry = isolated_registry

    return PersonFilterType


# ---------------------------------------------------------------------------
# get_field_type_from_registry
# ---------------------------------------------------------------------------


class TestGetFieldTypeFromRegistry:
    """Coverage for :func:`get_field_type_from_registry`.

    The helper is the only public renamed function in the refactor; it
    must continue to:

    * resolve the Graphene type for a registered model + field pair,
    * unwrap a ``NonNull`` wrapper so callers always receive the named
      type underneath,
    * return ``None`` when the model isn't registered, and
    * return ``None`` when the field name doesn't exist on the type.
    """

    def test_returns_field_type_for_registered_model(
        self, isolated_registry, reporter_type
    ):
        """
        Name: registered model resolves field type
        Description: When the registry has a DjangoObjectType for the model
            and that type exposes the requested field, return its Graphene
            type.
        Assumptions: ``ReporterFilterType`` is registered in the isolated
            registry and exposes ``first_name``.
        Expectations: The returned type is non-None.
        """
        result = get_field_type_from_registry(
            isolated_registry, Reporter, "first_name"
        )
        assert result is not None

    def test_unwraps_non_null(self, isolated_registry, reporter_type):
        """
        Name: NonNull wrapper unwrapped
        Description: When the resolved type is a ``NonNull`` wrapper, the
            helper must unwrap it so the caller can compose its own
            wrappers without double-wrapping.
        Assumptions: ``Reporter.first_name`` is a non-null CharField, which
            converts to ``NonNull(String)`` in graphene-django.
        Expectations: ``isinstance(result, NonNull)`` is False but
            ``isinstance(NonNull, ...)`` would have been True before
            unwrapping.
        """
        result = get_field_type_from_registry(
            isolated_registry, Reporter, "first_name"
        )
        assert not isinstance(result, NonNull), (
            f"expected unwrapped type, got NonNull-wrapped: {result!r}"
        )

    def test_returns_none_for_unregistered_model(self, isolated_registry):
        """
        Name: unregistered model returns None
        Description: When the requested model has no DjangoObjectType in
            the registry, the helper must short-circuit to ``None`` so the
            caller can fall back to converting the form field instead.
        Assumptions: ``Pet`` is not registered in this isolated registry.
        Expectations: Returns ``None``.
        """
        assert get_field_type_from_registry(isolated_registry, Pet, "name") is None

    def test_returns_none_for_unknown_field(
        self, isolated_registry, reporter_type
    ):
        """
        Name: unknown field returns None
        Description: When the model is registered but the requested field
            name doesn't exist on its type, the helper must return ``None``.
        Assumptions: ``ReporterFilterType`` does not declare a field
            named ``"nonexistent"``.
        Expectations: Returns ``None``.
        """
        assert (
            get_field_type_from_registry(isolated_registry, Reporter, "nonexistent")
            is None
        )


# ---------------------------------------------------------------------------
# _is_foreign_key_form_field
# ---------------------------------------------------------------------------


class TestIsForeignKeyFormField:
    """Coverage for :func:`_is_foreign_key_form_field`.

    The helper centralises the "form field maps to a foreign-key relation"
    predicate so the FK-routing logic in
    :func:`_get_field_type_from_model_field` stays readable.
    """

    @pytest.mark.parametrize(
        "form_field_class",
        [
            forms.ModelChoiceField,
            forms.ModelMultipleChoiceField,
            GlobalIDFormField,
            GlobalIDMultipleChoiceField,
        ],
    )
    def test_recognises_fk_form_fields(self, form_field_class):
        """
        Name: FK-style form fields recognised
        Description: All four FK-related form-field classes used by the
            implicit-filter resolution must be reported as foreign-key
            form fields so they get routed through the related model's id.
        Assumptions: The four parameterised classes are the canonical FK
            form fields handled by the resolver.
        Expectations: ``_is_foreign_key_form_field`` returns ``True``.
        """
        if form_field_class is forms.ModelChoiceField:
            instance = form_field_class(queryset=Person.objects.none())
        elif form_field_class is forms.ModelMultipleChoiceField:
            instance = form_field_class(queryset=Person.objects.none())
        else:
            instance = form_field_class()

        assert _is_foreign_key_form_field(instance) is True

    def test_plain_form_field_is_not_fk(self):
        """
        Name: plain form field is not FK
        Description: A plain ``CharField`` (or any non-FK form field) must
            be reported as a non-FK form field so the resolver routes it
            through the regular model-field path instead.
        Assumptions: ``forms.CharField`` is not in the FK-recognised set.
        Expectations: ``_is_foreign_key_form_field`` returns ``False``.
        """
        assert _is_foreign_key_form_field(forms.CharField()) is False


# ---------------------------------------------------------------------------
# _get_form_field
# ---------------------------------------------------------------------------


class TestGetFormField:
    """Coverage for :func:`_get_form_field` resolution rules.

    Resolution order:

    1. ``model_field.formfield(required=...)`` if the model field exposes
       a ``formfield`` factory and it returns a truthy value.
    2. ``filter_field.field`` otherwise (and when ``model_field`` is
       ``None``).
    """

    def test_uses_model_field_formfield_when_available(self):
        """
        Name: prefers model_field.formfield
        Description: When the underlying model field exposes a ``formfield``
            factory that returns a form field, that form field is used.
        Assumptions: ``Reporter._meta.get_field("first_name").formfield()``
            returns a non-None form field.
        Expectations: The returned form field is the one produced by
            ``model_field.formfield`` (a CharField for first_name), not the
            filter's own ``filter_field.field``.
        """
        model_field = Reporter._meta.get_field("first_name")
        filter_field = CharFilter()

        result = _get_form_field(model_field, filter_field, required=False)
        assert result is not filter_field.field
        assert isinstance(result, forms.CharField)

    def test_falls_back_to_filter_field_field_when_model_field_is_none(self):
        """
        Name: falls back to filter_field.field when model_field is None
        Description: When the resolver cannot find a model field for a
            filter (e.g. the filter targets an annotation or method-only
            attribute), the helper must use ``filter_field.field`` so
            validation does not lose its form field.
        Assumptions: ``CharFilter().field`` is a usable form field.
        Expectations: The returned form field is exactly ``filter_field.field``.
        """
        filter_field = CharFilter()
        result = _get_form_field(None, filter_field, required=False)
        assert result is filter_field.field

    def test_falls_back_when_model_field_formfield_returns_falsy(self):
        """
        Name: falls back when model_field.formfield returns falsy
        Description: Even when a model field has a ``formfield`` factory,
            the resolver must still fall back to ``filter_field.field`` if
            the factory returns a falsy value (e.g. for fields that are
            not user-editable).
        Assumptions: We can simulate a model field whose ``formfield``
            returns ``None`` using a tiny fake object.
        Expectations: The returned form field is exactly ``filter_field.field``.
        """

        class FakeModelField:
            def formfield(self, required):
                return None

        filter_field = CharFilter()
        result = _get_form_field(FakeModelField(), filter_field, required=False)
        assert result is filter_field.field


# ---------------------------------------------------------------------------
# _get_field_type_from_model_field
# ---------------------------------------------------------------------------


class TestGetFieldTypeFromModelField:
    """Coverage for :func:`_get_field_type_from_model_field`.

    For FK form fields the resolver must look up the related model's
    ``id`` in the registry; for non-FK form fields it must look up the
    owning model + field name directly.
    """

    def test_foreign_key_routes_through_related_model_id(
        self, isolated_registry, pet_type, person_type
    ):
        """
        Name: foreign key uses related model id
        Description: For an FK model field combined with an FK form field,
            the helper must resolve the type via the **related model**'s
            ``id`` field (since GraphQL filters on relations target the
            related node's identifier).
        Assumptions: ``Pet.owner`` is an FK to ``Person``; both types are
            registered in the isolated registry.
        Expectations: The returned type is non-None (Person.id resolves)
            and matches the type that ``get_field_type_from_registry``
            would return for ``Person.id`` directly.
        """
        owner_field = Pet._meta.get_field("owner")
        fk_form_field = forms.ModelChoiceField(queryset=Person.objects.none())

        result = _get_field_type_from_model_field(
            owner_field, fk_form_field, isolated_registry
        )
        expected = get_field_type_from_registry(isolated_registry, Person, "id")
        assert result is not None
        assert result == expected

    def test_non_foreign_key_routes_through_owning_model_field(
        self, isolated_registry, pet_type
    ):
        """
        Name: non-FK uses owning model field
        Description: For a non-FK model field, the helper must resolve the
            type via the owning model + the field name directly.
        Assumptions: ``Pet.name`` is a CharField on the registered
            ``PetFilterType``.
        Expectations: The returned type matches what
            ``get_field_type_from_registry`` returns for ``Pet.name``.
        """
        name_field = Pet._meta.get_field("name")
        plain_form_field = forms.CharField()

        result = _get_field_type_from_model_field(
            name_field, plain_form_field, isolated_registry
        )
        expected = get_field_type_from_registry(isolated_registry, Pet, "name")
        assert result == expected


# ---------------------------------------------------------------------------
# _get_field_type_and_form_field_for_implicit_filter
# ---------------------------------------------------------------------------


class TestGetFieldTypeAndFormFieldForImplicitFilter:
    """Coverage for :func:`_get_field_type_and_form_field_for_implicit_filter`.

    Branches:

    * ``filter_type == "isnull"`` short-circuits to ``(graphene.Boolean, None)``.
    * Real model field present -> ``(field_type_from_registry, form_field)``.
    * Model field absent -> ``(None, form_field)`` so the caller falls
      back to the explicit-filter path.
    """

    def test_isnull_short_circuits_to_boolean(self, isolated_registry, reporter_type):
        """
        Name: isnull -> Boolean
        Description: The ``isnull`` lookup is always boolean and needs no
            form field, so the helper short-circuits without touching the
            model.
        Assumptions: ``filter_type`` of ``"isnull"`` is the canonical key
            used by django-filter for null checks.
        Expectations: Returns ``(graphene.Boolean, None)``.
        """
        result = _get_field_type_and_form_field_for_implicit_filter(
            Reporter, "isnull", CharFilter(field_name="first_name"), isolated_registry, False
        )
        assert result == (graphene.Boolean, None)

    def test_returns_field_type_and_form_field_for_real_model_field(
        self, isolated_registry, reporter_type
    ):
        """
        Name: real model field returns (field_type, form_field)
        Description: For a filter targeting a real model field, the helper
            must return both the resolved Graphene type and the resolved
            form field so the caller can reuse them.
        Assumptions: ``Reporter.first_name`` exists and ``ReporterFilterType``
            is registered.
        Expectations: ``field_type`` is non-None and ``form_field`` is a
            ``forms.CharField`` (since first_name is a CharField).
        """
        field_type, form_field = _get_field_type_and_form_field_for_implicit_filter(
            Reporter,
            "exact",
            CharFilter(field_name="first_name"),
            isolated_registry,
            False,
        )
        assert field_type is not None
        assert isinstance(form_field, forms.CharField)

    def test_returns_none_for_missing_model_field(
        self, isolated_registry, reporter_type
    ):
        """
        Name: missing model field returns (None, form_field)
        Description: When the filter targets a name that is not a real
            model field, the helper must return ``(None, form_field)`` so
            the caller falls back to the explicit-filter conversion path.
        Assumptions: ``Reporter`` has no field named
            ``"nonexistent_attribute"``.
        Expectations: ``field_type`` is ``None`` and ``form_field`` is the
            filter's own field (since model_field is None).
        """
        char_filter = CharFilter(field_name="nonexistent_attribute")
        field_type, form_field = _get_field_type_and_form_field_for_implicit_filter(
            Reporter, "exact", char_filter, isolated_registry, False
        )
        assert field_type is None
        assert form_field is char_filter.field


# ---------------------------------------------------------------------------
# _get_field_type_for_explicit_filter
# ---------------------------------------------------------------------------


class TestGetFieldTypeForExplicitFilter:
    """Coverage for :func:`_get_field_type_for_explicit_filter`.

    The helper converts a Django form field into a Graphene type via
    :func:`graphene_django.forms.converter.convert_form_field`. It is
    used both for explicitly-declared filters and as the fallback when
    the implicit-filter path could not resolve a registry type.
    """

    def test_uses_passed_form_field_when_truthy(self):
        """
        Name: prefers passed form_field when truthy
        Description: When the caller has already resolved a form field,
            the helper should use it directly rather than falling back to
            ``filter_field.field``.
        Assumptions: ``forms.IntegerField()`` converts to a usable
            Graphene type via the form-field converter.
        Expectations: The returned type matches what
            ``convert_form_field(IntegerField())`` would yield.
        """
        from ...forms.converter import convert_form_field

        explicit = forms.IntegerField()
        filter_field = CharFilter()

        result = _get_field_type_for_explicit_filter(filter_field, explicit)
        expected = convert_form_field(explicit).get_type()
        assert result == expected

    def test_falls_back_to_filter_field_field_when_form_field_is_falsy(self):
        """
        Name: falls back to filter_field.field when form_field is falsy
        Description: When ``form_field`` is ``None``/falsy, the helper must
            fall back to ``filter_field.field`` so the explicit-filter path
            never converts a missing form field.
        Assumptions: ``CharFilter().field`` is a usable form field.
        Expectations: The returned type matches what
            ``convert_form_field(filter_field.field)`` would yield.
        """
        from ...forms.converter import convert_form_field

        filter_field = CharFilter()
        result = _get_field_type_for_explicit_filter(filter_field, None)
        expected = convert_form_field(filter_field.field).get_type()
        assert result == expected


# ---------------------------------------------------------------------------
# _is_filter_list_or_range
# ---------------------------------------------------------------------------


class TestIsFilterListOrRange:
    """Coverage for :func:`_is_filter_list_or_range`.

    Identifies ``ListFilter`` and ``RangeFilter`` so their argument type
    gets wrapped in ``graphene.List`` (the ``in`` and ``range`` lookups
    accept multiple values).
    """

    def test_list_filter_recognised(self):
        """
        Name: ListFilter recognised
        Description: A :class:`ListFilter` instance must be reported as a
            list/range filter so its argument gets wrapped in ``graphene.List``.
        Assumptions: ``ListFilter`` is the canonical implementation of
            list-typed filter arguments in graphene-django.
        Expectations: Returns ``True``.
        """
        assert _is_filter_list_or_range(ListFilter()) is True

    def test_range_filter_recognised(self):
        """
        Name: RangeFilter recognised
        Description: A :class:`RangeFilter` instance must be reported as a
            list/range filter so its argument gets wrapped in ``graphene.List``.
        Assumptions: ``RangeFilter`` is the canonical implementation of
            range-typed filter arguments in graphene-django.
        Expectations: Returns ``True``.
        """
        assert _is_filter_list_or_range(RangeFilter()) is True

    def test_plain_char_filter_not_recognised(self):
        """
        Name: plain CharFilter not list-or-range
        Description: A regular ``CharFilter`` must not be reported as a
            list/range filter so its argument stays scalar.
        Assumptions: ``django_filters.CharFilter`` is not a subclass of
            ``ListFilter`` or ``RangeFilter``.
        Expectations: Returns ``False``.
        """
        assert _is_filter_list_or_range(CharFilter()) is False


# ---------------------------------------------------------------------------
# Regression: get_filtering_args_from_filterset routes non-model fields
# correctly through the explicit-filter fallback.
# ---------------------------------------------------------------------------


class TestGetFilteringArgsFromFilterset:
    """Integration regression coverage for :func:`get_filtering_args_from_filterset`.

    This pins the subtle behavioural-parity concern flagged in the PR
    review: the implicit-filter helper now always calls ``_get_form_field``
    even when the model field is missing (returning ``(None, form_field)``),
    and the caller must still fall through to the explicit-filter helper
    so the Graphene Argument is built.
    """

    def test_filter_on_non_model_field_uses_explicit_fallback(
        self, isolated_registry, reporter_type
    ):
        """
        Name: filter on non-model field falls back to form-field conversion
        Description: When a FilterSet declares a filter targeting a name
            that is not a real model field (here, an annotation-style
            ``method`` filter), the resolver must still produce a Graphene
            ``Argument`` for it via the explicit-filter conversion path.
        Assumptions: ``django_filters.NumberFilter(method=...)`` declared on
            a FilterSet without a corresponding model field is a valid way
            to expose a method-backed filter; ``reporter_type`` registers a
            ``Reporter`` :class:`DjangoObjectType` in the isolated registry.
        Expectations: The returned arguments dict contains the filter
            name and yields a non-None Graphene ``Argument``.
        """

        class ReporterFilterSet(FilterSet):
            articles_count = NumberFilter(method="filter_by_articles_count")

            class Meta:
                model = Reporter
                fields = []

            def filter_by_articles_count(self, queryset, _name, value):
                return queryset

        args = get_filtering_args_from_filterset(ReporterFilterSet, reporter_type)
        assert "articles_count" in args
        argument = args["articles_count"]
        assert isinstance(argument, graphene.Argument)
        assert argument._type is not None
