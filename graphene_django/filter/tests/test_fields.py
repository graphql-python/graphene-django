from datetime import datetime
from textwrap import dedent

import pytest
from django.db.models import TextField, Value
from django.db.models.functions import Concat

from graphene import Argument, Boolean, Field, Float, ObjectType, Schema, String
from graphene.relay import Node
from graphene_django import DjangoObjectType
from graphene_django.forms import GlobalIDFormField, GlobalIDMultipleChoiceField
from graphene_django.tests.models import Article, Pet, Reporter
from graphene_django.utils import DJANGO_FILTER_INSTALLED

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    import django_filters
    from django_filters import FilterSet, NumberFilter

    from graphene_django.filter import (
        GlobalIDFilter,
        DjangoFilterConnectionField,
        GlobalIDMultipleChoiceFilter,
    )
    from graphene_django.filter.tests.filters import (
        ArticleFilter,
        PetFilter,
        ReporterFilter,
    )
else:
    pytestmark.append(
        pytest.mark.skipif(
            True, reason="django_filters not installed or not compatible"
        )
    )

if DJANGO_FILTER_INSTALLED:

    class ArticleNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ("headline",)

    class ReporterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    class PetNode(DjangoObjectType):
        class Meta:
            model = Pet
            interfaces = (Node,)
            fields = "__all__"


def get_args(field):
    return field.args


def assert_arguments(field, *arguments):
    ignore = ("after", "before", "first", "last", "order_by")
    args = get_args(field)
    actual = [name for name in args if name not in ignore and not name.startswith("_")]
    assert set(arguments) == set(
        actual
    ), "Expected arguments ({}) did not match actual ({})".format(arguments, actual)


def assert_orderable(field):
    args = get_args(field)
    assert "order_by" in args, "Field cannot be ordered"


def assert_not_orderable(field):
    args = get_args(field)
    assert "order_by" not in args, "Field can be ordered"


def test_filter_explicit_filterset_arguments():
    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleFilter)
    assert_arguments(
        field,
        "headline",
        "headline__icontains",
        "pub_date",
        "pub_date__gt",
        "pub_date__lt",
        "reporter",
    )


def test_filter_shortcut_filterset_arguments_list():
    field = DjangoFilterConnectionField(ArticleNode, fields=["pub_date", "reporter"])
    assert_arguments(field, "pub_date", "reporter")


def test_filter_shortcut_filterset_arguments_dict():
    field = DjangoFilterConnectionField(
        ArticleNode, fields={"headline": ["exact", "icontains"], "reporter": ["exact"]}
    )
    assert_arguments(field, "headline", "headline__icontains", "reporter")


def test_filter_explicit_filterset_orderable():
    field = DjangoFilterConnectionField(ReporterNode, filterset_class=ReporterFilter)
    assert_orderable(field)


# def test_filter_shortcut_filterset_orderable_true():
#     field = DjangoFilterConnectionField(ReporterNode)
#     assert_not_orderable(field)


# def test_filter_shortcut_filterset_orderable_headline():
#     field = DjangoFilterConnectionField(ReporterNode, order_by=['headline'])
#     assert_orderable(field)


def test_filter_explicit_filterset_not_orderable():
    field = DjangoFilterConnectionField(PetNode, filterset_class=PetFilter)
    assert_not_orderable(field)


def test_filter_shortcut_filterset_extra_meta():
    field = DjangoFilterConnectionField(
        ArticleNode, extra_filter_meta={"exclude": ("headline",)}
    )
    assert "headline" not in field.filterset_class.get_fields()


def test_filter_shortcut_filterset_context():
    class ArticleContextFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            exclude = set()

        @property
        def qs(self):
            qs = super(ArticleContextFilter, self).qs
            return qs.filter(reporter=self.request.reporter)

    class Query(ObjectType):
        context_articles = DjangoFilterConnectionField(
            ArticleNode, filterset_class=ArticleContextFilter
        )

    r1 = Reporter.objects.create(first_name="r1", last_name="r1", email="r1@test.com")
    r2 = Reporter.objects.create(first_name="r2", last_name="r2", email="r2@test.com")
    Article.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    Article.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    class context(object):
        reporter = r2

    query = """
    query {
        contextArticles {
            edges {
                node {
                    headline
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    result = schema.execute(query, context_value=context())
    assert not result.errors

    assert len(result.data["contextArticles"]["edges"]) == 1
    assert result.data["contextArticles"]["edges"][0]["node"]["headline"] == "a2"


def test_filter_filterset_information_on_meta():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ["first_name", "articles"]

    field = DjangoFilterConnectionField(ReporterFilterNode)
    assert_arguments(field, "first_name", "articles")
    assert_not_orderable(field)


def test_filter_filterset_information_on_meta_related():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ["first_name", "articles"]

    class ArticleFilterNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ["headline", "reporter"]

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)
        all_articles = DjangoFilterConnectionField(ArticleFilterNode)
        reporter = Field(ReporterFilterNode)
        article = Field(ArticleFilterNode)

    schema = Schema(query=Query)
    articles_field = ReporterFilterNode._meta.fields["articles"].get_type()
    assert_arguments(articles_field, "headline", "reporter")
    assert_not_orderable(articles_field)


def test_filter_filterset_class_filter_fields_exception():
    with pytest.raises(Exception):

        class ReporterFilter(FilterSet):
            class Meta:
                model = Reporter
                fields = ["first_name", "articles"]

        class ReporterFilterNode(DjangoObjectType):
            class Meta:
                model = Reporter
                interfaces = (Node,)
                fields = "__all__"
                filterset_class = ReporterFilter
                filter_fields = ["first_name", "articles"]


def test_filter_filterset_class_information_on_meta():
    class ReporterFilter(FilterSet):
        class Meta:
            model = Reporter
            fields = ["first_name", "articles"]

    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = ReporterFilter

    field = DjangoFilterConnectionField(ReporterFilterNode)
    assert_arguments(field, "first_name", "articles")
    assert_not_orderable(field)


def test_filter_filterset_class_information_on_meta_related():
    class ReporterFilter(FilterSet):
        class Meta:
            model = Reporter
            fields = ["first_name", "articles"]

    class ArticleFilter(FilterSet):
        class Meta:
            model = Article
            fields = ["headline", "reporter"]

    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = ReporterFilter

    class ArticleFilterNode(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = ArticleFilter

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)
        all_articles = DjangoFilterConnectionField(ArticleFilterNode)
        reporter = Field(ReporterFilterNode)
        article = Field(ArticleFilterNode)

    schema = Schema(query=Query)
    articles_field = ReporterFilterNode._meta.fields["articles"].get_type()
    assert_arguments(articles_field, "headline", "reporter")
    assert_not_orderable(articles_field)


def test_filter_filterset_related_results():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ["first_name", "articles"]

    class ArticleFilterNode(DjangoObjectType):
        class Meta:
            interfaces = (Node,)
            model = Article
            fields = "__all__"
            filter_fields = ["headline", "reporter"]

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)
        all_articles = DjangoFilterConnectionField(ArticleFilterNode)
        reporter = Field(ReporterFilterNode)
        article = Field(ArticleFilterNode)

    r1 = Reporter.objects.create(first_name="r1", last_name="r1", email="r1@test.com")
    r2 = Reporter.objects.create(first_name="r2", last_name="r2", email="r2@test.com")
    Article.objects.create(
        headline="a1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r1,
        editor=r1,
    )
    Article.objects.create(
        headline="a2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r2,
        editor=r2,
    )

    query = """
    query {
        allReporters {
            edges {
                node {
                    articles {
                        edges {
                            node {
                                headline
                            }
                        }
                    }
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    # We should only get back a single article for each reporter
    assert (
        len(result.data["allReporters"]["edges"][0]["node"]["articles"]["edges"]) == 1
    )
    assert (
        len(result.data["allReporters"]["edges"][1]["node"]["articles"]["edges"]) == 1
    )


def test_global_id_field_implicit():
    field = DjangoFilterConnectionField(ArticleNode, fields=["id"])
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["id"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_global_id_field_explicit():
    class ArticleIdFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            fields = ["id"]

    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleIdFilter)
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["id"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_filterset_descriptions():
    class ArticleIdFilter(django_filters.FilterSet):
        class Meta:
            model = Article
            fields = ["id"]

        max_time = django_filters.NumberFilter(
            method="filter_max_time", label="The maximum time"
        )

    field = DjangoFilterConnectionField(ArticleNode, filterset_class=ArticleIdFilter)
    max_time = field.args["max_time"]
    assert isinstance(max_time, Argument)
    assert max_time.type == Float
    assert max_time.description == "The maximum time"


def test_global_id_field_relation():
    field = DjangoFilterConnectionField(ArticleNode, fields=["reporter"])
    filterset_class = field.filterset_class
    id_filter = filterset_class.base_filters["reporter"]
    assert isinstance(id_filter, GlobalIDFilter)
    assert id_filter.field_class == GlobalIDFormField


def test_global_id_multiple_field_implicit():
    field = DjangoFilterConnectionField(ReporterNode, fields=["pets"])
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["pets"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_explicit():
    class ReporterPetsFilter(django_filters.FilterSet):
        class Meta:
            model = Reporter
            fields = ["pets"]

    field = DjangoFilterConnectionField(
        ReporterNode, filterset_class=ReporterPetsFilter
    )
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["pets"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_implicit_reverse():
    field = DjangoFilterConnectionField(ReporterNode, fields=["articles"])
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["articles"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_global_id_multiple_field_explicit_reverse():
    class ReporterPetsFilter(django_filters.FilterSet):
        class Meta:
            model = Reporter
            fields = ["articles"]

    field = DjangoFilterConnectionField(
        ReporterNode, filterset_class=ReporterPetsFilter
    )
    filterset_class = field.filterset_class
    multiple_filter = filterset_class.base_filters["articles"]
    assert isinstance(multiple_filter, GlobalIDMultipleChoiceFilter)
    assert multiple_filter.field_class == GlobalIDMultipleChoiceField


def test_filter_filterset_related_results_with_filter():
    class ReporterFilterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = {"first_name": ["icontains"]}

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)

    Reporter.objects.create(
        first_name="A test user", last_name="Last Name", email="test1@test.com"
    )
    Reporter.objects.create(
        first_name="Other test user",
        last_name="Other Last Name",
        email="test2@test.com",
    )
    Reporter.objects.create(
        first_name="Random", last_name="RandomLast", email="random@test.com"
    )

    query = """
    query {
        allReporters(firstName_Icontains: "test") {
            edges {
                node {
                    id
                }
            }
        }
    }
    """
    schema = Schema(query=Query)
    result = schema.execute(query)
    assert not result.errors
    # We should only get two reporters
    assert len(result.data["allReporters"]["edges"]) == 2


def test_recursive_filter_connection():
    class ReporterFilterNode(DjangoObjectType):
        child_reporters = DjangoFilterConnectionField(lambda: ReporterFilterNode)

        def resolve_child_reporters(self, **args):
            return []

        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterFilterNode)

    assert (
        ReporterFilterNode._meta.fields["child_reporters"].node_type
        == ReporterFilterNode
    )


def test_should_query_filter_node_limit():
    class ReporterFilter(FilterSet):
        limit = NumberFilter(method="filter_limit")

        def filter_limit(self, queryset, name, value):
            return queryset[:value]

        class Meta:
            model = Reporter
            fields = ["first_name"]

    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    class ArticleType(DjangoObjectType):
        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ("lang",)

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, filterset_class=ReporterFilter
        )

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.order_by("a_choice")

    Reporter.objects.create(
        first_name="Bob", last_name="Doe", email="bobdoe@example.com", a_choice=2
    )
    r = Reporter.objects.create(
        first_name="John", last_name="Doe", email="johndoe@example.com", a_choice=1
    )

    Article.objects.create(
        headline="Article Node 1",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r,
        editor=r,
        lang="es",
    )
    Article.objects.create(
        headline="Article Node 2",
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
        reporter=r,
        editor=r,
        lang="en",
    )

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(limit: 1) {
                edges {
                    node {
                        id
                        firstName
                        articles(lang: "es") {
                            edges {
                                node {
                                    id
                                    lang
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    expected = {
        "allReporters": {
            "edges": [
                {
                    "node": {
                        "id": "UmVwb3J0ZXJUeXBlOjI=",
                        "firstName": "John",
                        "articles": {
                            "edges": [
                                {"node": {"id": "QXJ0aWNsZVR5cGU6MQ==", "lang": "ES"}}
                            ]
                        },
                    }
                }
            ]
        }
    }

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_order_by_is_perserved():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ()

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, reverse_order=Boolean()
        )

        def resolve_all_reporters(self, info, reverse_order=False, **args):
            reporters = Reporter.objects.order_by("first_name")

            if reverse_order:
                return reporters.reverse()

            return reporters

    Reporter.objects.create(first_name="b")
    Reporter.objects.create(first_name="a")

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"firstName": "a"}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected

    reverse_query = """
        query NodeFilteringQuery {
            allReporters(first: 1, reverseOrder: true) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """

    reverse_expected = {"allReporters": {"edges": [{"node": {"firstName": "b"}}]}}

    reverse_result = schema.execute(reverse_query)

    assert not reverse_result.errors
    assert reverse_result.data == reverse_expected


def test_annotation_is_preserved():
    class ReporterType(DjangoObjectType):
        full_name = String()

        def resolve_full_name(instance, info, **args):
            return instance.full_name

        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ()

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.annotate(
                full_name=Concat(
                    "first_name", Value(" "), "last_name", output_field=TextField()
                )
            )

    Reporter.objects.create(first_name="John", last_name="Doe")

    schema = Schema(query=Query)

    query = """
        query NodeFilteringQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        fullName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"fullName": "John Doe"}}]}}

    result = schema.execute(query)

    assert not result.errors
    assert result.data == expected


def test_annotation_with_only():
    class ReporterType(DjangoObjectType):
        full_name = String()

        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ()

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(ReporterType)

        def resolve_all_reporters(self, info, **args):
            return Reporter.objects.only("first_name", "last_name").annotate(
                full_name=Concat(
                    "first_name", Value(" "), "last_name", output_field=TextField()
                )
            )

    Reporter.objects.create(first_name="John", last_name="Doe")

    schema = Schema(query=Query)

    query = """
        query NodeFilteringQuery {
            allReporters(first: 1) {
                edges {
                    node {
                        fullName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"fullName": "John Doe"}}]}}

    result = schema.execute(query)

    assert not result.errors
    assert result.data == expected


def test_node_get_queryset_is_called():
    class ReporterType(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"
            filter_fields = ()

        @classmethod
        def get_queryset(cls, queryset, info):
            return queryset.filter(first_name="b")

    class Query(ObjectType):
        all_reporters = DjangoFilterConnectionField(
            ReporterType, reverse_order=Boolean()
        )

    Reporter.objects.create(first_name="b")
    Reporter.objects.create(first_name="a")

    schema = Schema(query=Query)
    query = """
        query NodeFilteringQuery {
            allReporters(first: 10) {
                edges {
                    node {
                        firstName
                    }
                }
            }
        }
    """
    expected = {"allReporters": {"edges": [{"node": {"firstName": "b"}}]}}

    result = schema.execute(query)
    assert not result.errors
    assert result.data == expected


def test_integer_field_filter_type():
    class PetType(DjangoObjectType):
        class Meta:
            model = Pet
            interfaces = (Node,)
            filter_fields = {"age": ["exact"]}
            fields = ("age",)

    class Query(ObjectType):
        pets = DjangoFilterConnectionField(PetType)

    schema = Schema(query=Query)

    assert str(schema) == dedent(
        """\
        type Query {
          pets(before: String = null, after: String = null, first: Int = null, last: Int = null, age: Int = null): PetTypeConnection
        }

        type PetTypeConnection {
          \"""Pagination data for this connection.\"""
          pageInfo: PageInfo!

          \"""Contains the nodes in this connection.\"""
          edges: [PetTypeEdge]!
        }

        \"""
        The Relay compliant `PageInfo` type, containing data necessary to paginate this connection.
        \"""
        type PageInfo {
          \"""When paginating forwards, are there more items?\"""
          hasNextPage: Boolean!
    
          \"""When paginating backwards, are there more items?\"""
          hasPreviousPage: Boolean!
    
          \"""When paginating backwards, the cursor to continue.\"""
          startCursor: String
    
          \"""When paginating forwards, the cursor to continue.\"""
          endCursor: String
        }
    
        \"""A Relay edge containing a `PetType` and its cursor.\"""
        type PetTypeEdge {
          \"""The item at the end of the edge\"""
          node: PetType
    
          \"""A cursor for use in pagination\"""
          cursor: String!
        }
    
        type PetType implements Node {
          age: Int!
    
          \"""The ID of the object\"""
          id: ID!
        }
    
        \"""An object with an ID\"""
        interface Node {
          \"""The ID of the object\"""
          id: ID!
        }
    """
    )


def test_other_filter_types():
    class PetType(DjangoObjectType):
        class Meta:
            model = Pet
            interfaces = (Node,)
            filter_fields = {"age": ["exact", "isnull", "lt"]}
            fields = ("age",)

    class Query(ObjectType):
        pets = DjangoFilterConnectionField(PetType)

    schema = Schema(query=Query)

    assert str(schema) == dedent(
        """\
        type Query {
          pets(before: String = null, after: String = null, first: Int = null, last: Int = null, age: Int = null, age_Isnull: Boolean = null, age_Lt: Int = null): PetTypeConnection
        }

        type PetTypeConnection {
          \"""Pagination data for this connection.\"""
          pageInfo: PageInfo!
          
          \"""Contains the nodes in this connection.\"""
          edges: [PetTypeEdge]!
        }

        \"""
        The Relay compliant `PageInfo` type, containing data necessary to paginate this connection.
        \"""
        type PageInfo {
          \"""When paginating forwards, are there more items?\"""
          hasNextPage: Boolean!

          \"""When paginating backwards, are there more items?\"""
          hasPreviousPage: Boolean!

          \"""When paginating backwards, the cursor to continue.\"""
          startCursor: String

          \"""When paginating forwards, the cursor to continue.\"""
          endCursor: String
        }

        \"""A Relay edge containing a `PetType` and its cursor.\"""
        type PetTypeEdge {
          \"""The item at the end of the edge\"""
          node: PetType
        
          \"""A cursor for use in pagination\"""
          cursor: String!
        }

        type PetType implements Node {
          age: Int!
        
          \"""The ID of the object\"""
          id: ID!
        }

        \"""An object with an ID\"""
        interface Node {
          \"""The ID of the object\"""
          id: ID!
        }
        """
    )


def test_filter_filterset_based_on_mixin():
    class ArticleFilterMixin(FilterSet):
        @classmethod
        def get_filters(cls):
            filters = super(FilterSet, cls).get_filters()
            filters.update(
                {
                    "viewer__email__in": django_filters.CharFilter(
                        method="filter_email_in", field_name="reporter__email__in"
                    )
                }
            )

            return filters

        def filter_email_in(cls, queryset, name, value):
            return queryset.filter(**{name: [value]})

    class NewArticleFilter(ArticleFilterMixin, ArticleFilter):
        pass

    class NewReporterNode(DjangoObjectType):
        class Meta:
            model = Reporter
            interfaces = (Node,)
            fields = "__all__"

    class NewArticleFilterNode(DjangoObjectType):
        viewer = Field(NewReporterNode)

        class Meta:
            model = Article
            interfaces = (Node,)
            fields = "__all__"
            filterset_class = NewArticleFilter

        def resolve_viewer(self, info):
            return self.reporter

    class Query(ObjectType):
        all_articles = DjangoFilterConnectionField(NewArticleFilterNode)

    reporter_1 = Reporter.objects.create(
        first_name="John", last_name="Doe", email="john@doe.com"
    )

    article_1 = Article.objects.create(
        headline="Hello",
        reporter=reporter_1,
        editor=reporter_1,
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
    )

    reporter_2 = Reporter.objects.create(
        first_name="Adam", last_name="Doe", email="adam@doe.com"
    )

    article_2 = Article.objects.create(
        headline="Good Bye",
        reporter=reporter_2,
        editor=reporter_2,
        pub_date=datetime.now(),
        pub_date_time=datetime.now(),
    )

    schema = Schema(query=Query)

    query = (
        """
        query NodeFilteringQuery {
            allArticles(viewer_Email_In: "%s") {
                edges {
                    node {
                        headline
                        viewer {
                            email
                        }
                    }
                }
            }
        }
    """
        % reporter_1.email
    )

    expected = {
        "allArticles": {
            "edges": [
                {
                    "node": {
                        "headline": article_1.headline,
                        "viewer": {"email": reporter_1.email},
                    }
                }
            ]
        }
    }

    result = schema.execute(query)

    assert not result.errors
    assert result.data == expected
