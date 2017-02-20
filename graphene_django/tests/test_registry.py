from pytest import raises

from ..registry import Registry, get_global_registry, reset_global_registry
from ..types import DjangoObjectType
from .models import Reporter as ReporterModel


def setup_function(function):
  reset_global_registry()


def test_registry_basic():
    global_registry = get_global_registry()
    
    class Reporter(DjangoObjectType):
        '''Reporter description'''
        class Meta:
            model = ReporterModel

    assert Reporter._meta.registry == global_registry
    assert global_registry.get_unique_type_for_model(ReporterModel) == Reporter


def test_registry_multiple_types():
    global_registry = get_global_registry()

    class Reporter(DjangoObjectType):
        '''Reporter description'''
        class Meta:
            model = ReporterModel

    class Reporter2(DjangoObjectType):
        '''Reporter2 description'''
        class Meta:
            model = ReporterModel

    assert global_registry.get_types_for_model(ReporterModel) == [Reporter, Reporter2]

    with raises(Exception) as exc_info:
        global_registry.get_unique_type_for_model(ReporterModel) == [Reporter, Reporter2]

    assert str(exc_info.value) == (
       'Found multiple ObjectTypes associated with the same '
       'Django Model "tests.Reporter": {}. You can use a different '
       'registry for each or skip the global Registry with '
       'Meta.skip_global_registry = True". '
       'Read more at http://docs.graphene-python.org/projects/django/en/latest/registry/ .'
    ).format(repr([Reporter, Reporter2]))


def test_registry_multiple_types_dont_collision_if_skip_global_registry():
    class Reporter(DjangoObjectType):
        '''Reporter description'''
        class Meta:
            model = ReporterModel

    class Reporter2(DjangoObjectType):
        '''Reporter2 description'''
        class Meta:
            model = ReporterModel
            skip_global_registry = True

    assert Reporter._meta.registry != Reporter2._meta.registry
    assert Reporter2._meta.registry != get_global_registry()
