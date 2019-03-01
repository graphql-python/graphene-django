from ..utils import get_model_fields, has_permissions
from .models import Film, Reporter


def test_get_model_fields_no_duplication():
    reporter_fields = get_model_fields(Reporter)
    reporter_name_set = set([field[0] for field in reporter_fields])
    assert len(reporter_fields) == len(reporter_name_set)

    film_fields = get_model_fields(Film)
    film_name_set = set([field[0] for field in film_fields])
    assert len(film_fields) == len(film_name_set)


def test_has_permissions():
    class Viewer(object):
        @staticmethod
        def has_perm(permission):
            return permission

    viewer_as_perm = has_permissions(Viewer(), [False, True, False])
    assert viewer_as_perm


def test_viewer_without_permissions():
    class Viewer(object):
        @staticmethod
        def has_perm(permission):
            return permission

    viewer_as_perm = has_permissions(Viewer(), [False, False, False])
    assert not viewer_as_perm
