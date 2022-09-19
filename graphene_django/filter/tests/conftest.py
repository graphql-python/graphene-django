from mock import MagicMock
import pytest

from django.db import models
from django.db.models.query import QuerySet
from django_filters import filters
from django_filters import FilterSet
import graphene
from graphene.relay import Node
from graphene_django import DjangoObjectType
from graphene_django.utils import DJANGO_FILTER_INSTALLED
from graphene_django.filter import ArrayFilter, ListFilter

from ...compat import ArrayField

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    from graphene_django.filter import DjangoFilterConnectionField
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )


STORE = {"events": []}


class Event(models.Model):
    name = models.CharField(max_length=50)
    tags = ArrayField(models.CharField(max_length=50))
    tag_ids = ArrayField(models.IntegerField())
    random_field = ArrayField(models.BooleanField())


@pytest.fixture
def EventFilterSet():
    class EventFilterSet(FilterSet):
        class Meta:
            model = Event
            fields = {
                "name": ["exact", "contains"],
            }

        # Those are actually usable with our Query fixture bellow
        tags__contains = ArrayFilter(field_name="tags", lookup_expr="contains")
        tags__overlap = ArrayFilter(field_name="tags", lookup_expr="overlap")
        tags = ArrayFilter(field_name="tags", lookup_expr="exact")

        # Those are actually not usable and only to check type declarations
        tags_ids__contains = ArrayFilter(field_name="tag_ids", lookup_expr="contains")
        tags_ids__overlap = ArrayFilter(field_name="tag_ids", lookup_expr="overlap")
        tags_ids = ArrayFilter(field_name="tag_ids", lookup_expr="exact")
        random_field__contains = ArrayFilter(
            field_name="random_field", lookup_expr="contains"
        )
        random_field__overlap = ArrayFilter(
            field_name="random_field", lookup_expr="overlap"
        )
        random_field = ArrayFilter(field_name="random_field", lookup_expr="exact")

    return EventFilterSet


@pytest.fixture
def EventType(EventFilterSet):
    class EventType(DjangoObjectType):
        class Meta:
            model = Event
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = EventFilterSet

    return EventType


@pytest.fixture
def Query(EventType):
    """
    Note that we have to use a custom resolver to replicate the arrayfield filter behavior as
    we are running unit tests in sqlite which does not have ArrayFields.
    """

    class Query(graphene.ObjectType):
        events = DjangoFilterConnectionField(EventType)

        def resolve_events(self, info, **kwargs):

            events = [
                Event(name="Live Show", tags=["concert", "music", "rock"]),
                Event(name="Musical", tags=["movie", "music"]),
                Event(name="Ballet", tags=["concert", "dance"]),
                Event(name="Speech", tags=[]),
            ]

            STORE["events"] = events

            m_queryset = MagicMock(spec=QuerySet)
            m_queryset.model = Event

            def filter_events(**kwargs):
                if "tags__contains" in kwargs:
                    STORE["events"] = list(
                        filter(
                            lambda e: set(kwargs["tags__contains"]).issubset(
                                set(e.tags)
                            ),
                            STORE["events"],
                        )
                    )
                if "tags__overlap" in kwargs:
                    STORE["events"] = list(
                        filter(
                            lambda e: not set(kwargs["tags__overlap"]).isdisjoint(
                                set(e.tags)
                            ),
                            STORE["events"],
                        )
                    )
                if "tags__exact" in kwargs:
                    STORE["events"] = list(
                        filter(
                            lambda e: set(kwargs["tags__exact"]) == set(e.tags),
                            STORE["events"],
                        )
                    )

            def mock_queryset_filter(*args, **kwargs):
                filter_events(**kwargs)
                return m_queryset

            def mock_queryset_none(*args, **kwargs):
                STORE["events"] = []
                return m_queryset

            def mock_queryset_count(*args, **kwargs):
                return len(STORE["events"])

            m_queryset.all.return_value = m_queryset
            m_queryset.filter.side_effect = mock_queryset_filter
            m_queryset.none.side_effect = mock_queryset_none
            m_queryset.count.side_effect = mock_queryset_count
            m_queryset.__getitem__.side_effect = lambda index: STORE[
                "events"
            ].__getitem__(index)

            return m_queryset

    return Query
