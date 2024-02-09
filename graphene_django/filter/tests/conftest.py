from functools import reduce

import pytest
from django.db import models
from django.db.models.query import QuerySet
from django_filters import FilterSet

import graphene
from graphene.relay import Node
from graphene_django import DjangoObjectType
from graphene_django.filter import ArrayFilter
from graphene_django.utils import DJANGO_FILTER_INSTALLED

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


class Event(models.Model):
    class Meta:
        ordering = ["pk"]

    name = models.CharField(max_length=50)
    tags = ArrayField(models.CharField(max_length=50))
    tag_ids = ArrayField(models.IntegerField())
    random_field = ArrayField(models.BooleanField())

    def __repr__(self):
        return f"Event [{self.name}]"


@pytest.fixture
def EventFilterSet():
    class EventFilterSet(FilterSet):
        class Meta:
            model = Event
            fields = {
                "name": ["exact", "contains"],
            }

        # Those are actually usable with our Query fixture below
        tags__contains = ArrayFilter(field_name="tags", lookup_expr="contains")
        tags__overlap = ArrayFilter(field_name="tags", lookup_expr="overlap")
        tags = ArrayFilter(field_name="tags", lookup_expr="exact")
        tags__len = ArrayFilter(
            field_name="tags", lookup_expr="len", input_type=graphene.Int
        )
        tags__len__in = ArrayFilter(
            field_name="tags",
            method="tags__len__in_filter",
            input_type=graphene.List(graphene.Int),
        )

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

        def tags__len__in_filter(self, queryset, _name, value):
            if not value:
                return queryset.none()
            return reduce(
                lambda q1, q2: q1.union(q2),
                [queryset.filter(tags__len=v) for v in value],
            ).distinct()

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

    events = [
        Event(name="Live Show", tags=["concert", "music", "rock"]),
        Event(name="Musical", tags=["movie", "music"]),
        Event(name="Ballet", tags=["concert", "dance"]),
        Event(name="Speech", tags=[]),
    ]

    class Query(graphene.ObjectType):
        events = DjangoFilterConnectionField(EventType)

        def resolve_events(self, info, **kwargs):
            class FakeQuerySet(QuerySet):
                def __init__(self, model=None):
                    self.model = Event
                    self.__store = list(events)

                def all(self):
                    return self

                def filter(self, **kwargs):
                    queryset = FakeQuerySet()
                    queryset.__store = list(self.__store)
                    if "tags__contains" in kwargs:
                        queryset.__store = list(
                            filter(
                                lambda e: set(kwargs["tags__contains"]).issubset(
                                    set(e.tags)
                                ),
                                queryset.__store,
                            )
                        )
                    if "tags__overlap" in kwargs:
                        queryset.__store = list(
                            filter(
                                lambda e: not set(kwargs["tags__overlap"]).isdisjoint(
                                    set(e.tags)
                                ),
                                queryset.__store,
                            )
                        )
                    if "tags__exact" in kwargs:
                        queryset.__store = list(
                            filter(
                                lambda e: set(kwargs["tags__exact"]) == set(e.tags),
                                queryset.__store,
                            )
                        )
                    if "tags__len" in kwargs:
                        queryset.__store = list(
                            filter(
                                lambda e: len(e.tags) == kwargs["tags__len"],
                                queryset.__store,
                            )
                        )
                    return queryset

                def union(self, *args):
                    queryset = FakeQuerySet()
                    queryset.__store = self.__store
                    for arg in args:
                        queryset.__store += arg.__store
                    return queryset

                def none(self):
                    queryset = FakeQuerySet()
                    queryset.__store = []
                    return queryset

                def count(self):
                    return len(self.__store)

                def distinct(self):
                    queryset = FakeQuerySet()
                    queryset.__store = []
                    for event in self.__store:
                        if event not in queryset.__store:
                            queryset.__store.append(event)
                    queryset.__store = sorted(queryset.__store, key=lambda e: e.name)
                    return queryset

                def __getitem__(self, index):
                    return self.__store[index]

            return FakeQuerySet()

    return Query


@pytest.fixture
def schema(Query):
    return graphene.Schema(query=Query)
