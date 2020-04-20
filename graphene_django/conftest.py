import pytest

from graphene_django.settings import graphene_settings as gsettings

from .registry import reset_global_registry


@pytest.fixture(autouse=True)
def reset_registry_fixture(db):
    yield None
    reset_global_registry()


@pytest.fixture()
def graphene_settings():
    settings = dict(gsettings.__dict__)
    yield gsettings
    gsettings.__dict__ = settings
