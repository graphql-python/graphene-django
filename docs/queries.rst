.. _queries-objecttypes:

Queries & ObjectTypes
=====================

Introduction
------------

Graphene-Django offers a host of features for performing GraphQL queries.

Graphene-Django ships with a special ``DjangoObjectType`` that automatically transforms a Django Model
into a ``ObjectType`` for you.


Full example
~~~~~~~~~~~~

.. code:: python

    # my_app/schema.py

    import graphene
    from graphene_django import DjangoObjectType

    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = ("id", "question_text")

    class Query(graphene.ObjectType):
        questions = graphene.List(QuestionType)
        question_by_id = graphene.Field(QuestionType, id=graphene.String())

        def resolve_questions(root, info, **kwargs):
            # Querying a list
            return Question.objects.all()

        def resolve_question_by_id(root, info, id):
            # Querying a single question
            return Question.objects.get(pk=id)


Specifying which fields to include
----------------------------------

By default, ``DjangoObjectType`` will present all fields on a Model through GraphQL.
If you only want a subset of fields to be present, you can do so using
``fields`` or ``exclude``. It is strongly recommended that you explicitly set
all fields that should be exposed using the fields attribute.
This will make it less likely to result in unintentionally exposing data when
your models change.

Setting neither ``fields`` nor ``exclude`` is deprecated and will raise a warning, you should at least explicitly make
``DjangoObjectType`` include all fields in the model as described below.

``fields``
~~~~~~~~~~

Show **only** these fields on the model:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = ("id", "question_text")

You can also set the ``fields`` attribute to the special value ``"__all__"`` to indicate that all fields in the model should be used.

For example:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = "__all__"


``exclude``
~~~~~~~~~~~

Show all fields **except** those in ``exclude``:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            exclude = ("question_text",)


Customising fields
------------------

You can completely overwrite a field, or add new fields, to a ``DjangoObjectType`` using a Resolver:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):

        class Meta:
            model = Question
            fields = ("id", "question_text")

        extra_field = graphene.String()

        def resolve_extra_field(self, info):
            return "hello!"


Choices to Enum conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default Graphene-Django will convert any Django fields that have `choices`_
defined into a GraphQL enum type.

.. _choices: https://docs.djangoproject.com/en/2.2/ref/models/fields/#choices

For example the following ``Model`` and ``DjangoObjectType``:

.. code:: python

    from django.db import models
    from graphene_django import DjangoObjectType

    class PetModel(models.Model):
        kind = models.CharField(
            max_length=100,
            choices=(("cat", "Cat"), ("dog", "Dog"))
        )

    class Pet(DjangoObjectType):
        class Meta:
            model = PetModel
            fields = ("id", "kind",)

Results in the following GraphQL schema definition:

.. code:: graphql

   type Pet {
     id: ID!
     kind: PetModelKind!
   }

   enum PetModelKind {
     CAT
     DOG
   }

You can disable this automatic conversion by setting
``convert_choices_to_enum`` attribute to ``False`` on the ``DjangoObjectType``
``Meta`` class.

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import PetModel

    class Pet(DjangoObjectType):
        class Meta:
            model = PetModel
            fields = ("id", "kind",)
            convert_choices_to_enum = False

.. code:: graphql

  type Pet {
    id: ID!
    kind: String!
  }

You can also set ``convert_choices_to_enum`` to a list of fields that should be
automatically converted into enums:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import PetModel

    class Pet(DjangoObjectType):
        class Meta:
            model = PetModel
            fields = ("id", "kind",)
            convert_choices_to_enum = ["kind"]

**Note:** Setting ``convert_choices_to_enum = []`` is the same as setting it to
``False``.


Related models
--------------

Say you have the following models:

.. code:: python

    from django.db import models

    class Category(models.Model):
        foo = models.CharField(max_length=256)

    class Question(models.Model):
        category = models.ForeignKey(Category, on_delete=models.CASCADE)


When ``Question`` is published as a ``DjangoObjectType`` and you want to add ``Category`` as a query-able field like so:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = ("category",)

Then all query-able related models must be defined as DjangoObjectType subclass,
or they will fail to show if you are trying to query those relation fields. You only
need to create the most basic class for this to work:

.. code:: python

    from graphene_django import DjangoObjectType
    from .models import Category

    class CategoryType(DjangoObjectType):
        class Meta:
            model = Category
            fields = ("foo",)

.. _django-objecttype-get-queryset:

Default QuerySet
-----------------

If you are using ``DjangoObjectType`` you can define a custom `get_queryset` method.
Use this to control filtering on the ObjectType level instead of the Query object level.

.. code:: python

    from graphene_django.types import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            fields = "__all__"

        @classmethod
        def get_queryset(cls, queryset, info):
            if info.context.user.is_anonymous:
                return queryset.filter(published=True)
            return queryset

Resolvers
---------

When a GraphQL query is received by the ``Schema`` object, it will map it to a "Resolver" related to it.

This resolve method should follow this format:

.. code:: python

    def resolve_foo(parent, info, **kwargs):

Where "foo" is the name of the field declared in the ``Query`` object.

.. code:: python

    import graphene
    from .models import Question
    from .types import QuestionType

    class Query(graphene.ObjectType):
        foo = graphene.List(QuestionType)

        def resolve_foo(root, info, **kwargs):
            id = kwargs.get("id")
            return Question.objects.get(id)

Arguments
~~~~~~~~~

Additionally, Resolvers will receive **any arguments declared in the field definition**. This allows you to provide input arguments in your GraphQL server and can be useful for custom queries.

.. code:: python

    import graphene
    from .models import Question
    from .types import QuestionType

    class Query(graphene.ObjectType):
        question = graphene.Field(
            QuestionType,
            foo=graphene.String(),
            bar=graphene.Int()
        )

        def resolve_question(root, info, foo=None, bar=None):
            # If `foo` or `bar` are declared in the GraphQL query they will be here, else None.
            return Question.objects.filter(foo=foo, bar=bar).first()


Info
~~~~

The ``info`` argument passed to all resolve methods holds some useful information.
For Graphene-Django, the ``info.context`` attribute is the ``HTTPRequest`` object
that would be familiar to any Django developer. This gives you the full functionality
of Django's ``HTTPRequest`` in your resolve methods, such as checking for authenticated users:

.. code:: python

    import graphene

    from .models import Question
    from .types import QuestionType

    class Query(graphene.ObjectType):
        questions = graphene.List(QuestionType)

        def resolve_questions(root, info):
            # See if a user is authenticated
            if info.context.user.is_authenticated():
                return Question.objects.all()
            else:
                return Question.objects.none()


DjangoObjectTypes
~~~~~~~~~~~~~~~~~

A Resolver that maps to a defined `DjangoObjectType` should only use methods that return a queryset.
Queryset methods like `values` will return dictionaries, use `defer` instead.


Plain ObjectTypes
-----------------

With Graphene-Django you are not limited to just Django Models - you can use the standard
``ObjectType`` to create custom fields or to provide an abstraction between your internal
Django models and your external API.

.. code:: python

    import graphene
    from .models import Question

    class MyQuestion(graphene.ObjectType):
        text = graphene.String()

    class Query(graphene.ObjectType):
        question = graphene.Field(MyQuestion, question_id=graphene.String())

        def resolve_question(root, info, question_id):
            question = Question.objects.get(pk=question_id)
            return MyQuestion(
                text=question.question_text
            )

For more information and more examples, please see the `core object type documentation <https://docs.graphene-python.org/en/latest/types/objecttypes/>`__.


Relay
-----

`Relay <http://docs.graphene-python.org/en/latest/relay/>`__ with Graphene-Django gives us some additional features:

- Pagination and slicing.
- An abstract ``id`` value which contains enough info for the server to know its type and its id.

There is one additional import and a single line of code needed to adopt this:

Full example
~~~~~~~~~~~~
See the `Relay documentation <https://docs.graphene-python.org/en/latest/relay/nodes/>`__ on
the core graphene pages for more information on customizing the Relay experience.

.. code:: python

    from graphene import relay
    from graphene_django import DjangoObjectType
    from .models import Question

    class QuestionType(DjangoObjectType):
        class Meta:
            model = Question
            interfaces = (relay.Node,)  # make sure you add this
            fields = "__all__"

    class QuestionConnection(relay.Connection):
        class Meta:
            node = QuestionType

    class Query:
        questions = relay.ConnectionField(QuestionConnection)

        def resolve_questions(root, info, **kwargs):
            return Question.objects.all()

You can now execute queries like:


.. code:: graphql

    {
        questions (first: 2, after: "YXJyYXljb25uZWN0aW9uOjEwNQ==") {
            pageInfo {
                startCursor
                endCursor
                hasNextPage
                hasPreviousPage
            }
            edges {
                cursor
                node {
                    id
                    question_text
                }
            }
        }
    }

Which returns:

.. code:: json

    {
        "data": {
            "questions": {
            "pageInfo": {
                "startCursor": "YXJyYXljb25uZWN0aW9uOjEwNg==",
                "endCursor": "YXJyYXljb25uZWN0aW9uOjEwNw==",
                "hasNextPage": true,
                "hasPreviousPage": false
            },
            "edges": [
                {
                "cursor": "YXJyYXljb25uZWN0aW9uOjEwNg==",
                "node": {
                    "id": "UGxhY2VUeXBlOjEwNw==",
                    "question_text": "How did we get here?"
                }
                },
                {
                "cursor": "YXJyYXljb25uZWN0aW9uOjEwNw==",
                "node": {
                    "id": "UGxhY2VUeXBlOjEwOA==",
                    "name": "Where are we?"
                }
                }
            ]
            }
        }
    }

Note that relay implements :code:`pagination` capabilities automatically, adding a :code:`pageInfo` element, and including :code:`cursor` on nodes. These elements are included in the above example for illustration.

To learn more about Pagination in general, take a look at `Pagination <https://graphql.org/learn/pagination/>`__  on the GraphQL community site.
