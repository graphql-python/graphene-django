Authorization in Django
=======================

There are several ways you may want to limit access to data when
working with Graphene and Django: limiting which fields are accessible
via GraphQL and limiting which objects a user can access.

Let's use a simple example model.

.. code:: python

    from django.db import models

    class Post(models.Model):
        title = models.CharField(max_length=100)
        content = models.TextField()
        published = models.BooleanField(default=False)
        owner = models.ForeignKey('auth.User')

Limiting Field Access
---------------------

This is easy, simply use the ``only_fields`` meta attribute.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            only_fields = ('title', 'content')
            interfaces = (relay.Node, )

conversely you can use ``exclude_fields`` meta atrribute.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            exclude_fields = ('published', 'owner')
            interfaces = (relay.Node, )

Queryset Filtering On Lists
---------------------------

In order to filter which objects are available in a queryset-based list,
define a resolve method for that field and return the desired queryset.

.. code:: python

    from graphene import ObjectType
    from graphene_django.filter import DjangoFilterConnectionField
    from .models import Post

    class Query(ObjectType):
        all_posts = DjangoFilterConnectionField(CategoryNode)

        def resolve_all_posts(self, args, info):
            return Post.objects.filter(published=True)

User-based Queryset Filtering
-----------------------------

If you are using ``GraphQLView`` you can access Django's request
with the context argument.

.. code:: python

    from graphene import ObjectType
    from graphene_django.filter import DjangoFilterConnectionField
    from .models import Post

    class Query(ObjectType):
        my_posts = DjangoFilterConnectionField(CategoryNode)

        def resolve_my_posts(self, info):
            # context will reference to the Django request
            if not info.context.user.is_authenticated():
                return Post.objects.none()
            else:
                return Post.objects.filter(owner=info.context.user)

If you're using your own view, passing the request context into the
schema is simple.

.. code:: python

    result = schema.execute(query, context_value=request)

Filtering ID-based node access
------------------------------

In order to add authorization to id-based node access, we need to add a
method to your ``DjangoObjectType``.

.. code:: python

    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            only_fields = ('title', 'content')
            interfaces = (relay.Node, )

        @classmethod
        def get_node(cls, id, context, info):
            try:
                post = cls._meta.model.objects.get(id=id)
            except cls._meta.model.DoesNotExist:
                return None

            if post.published or context.user == post.owner:
                return post
            return None

Require permissions
---------------------

If you want you can require Django permissions to access to *Nodes*,
*Mutations* and *Connections*.

Node example:

.. code:: python
    from graphene_django.types import DjangoObjectType
    from graphene_django.auth import node_require_permission
    from .models import Reporter

    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_report',, 'can_edit_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

Mutation example:

.. code:: python
    from rest_framework import serializers
    from graphene_django.types import DjangoObjectType
    from graphene_django.auth import node_require_permission
    from graphene_django.rest_framework.mutation import SerializerMutation
    from .models import Reporter


    class ReporterSerializer(serializers.ModelSerializer):
        class Meta:
            model = Reporter
            fields = '__all__'


    class MyMutation(SerializerMutation):
        class Meta:
            serializer_class = ReporterSerializer

        @classmethod
        @mutation_require_permission(permissions=('can_view_foo', 'can_edit_foo', ))
        def mutate_and_get_payload(cls, root, info, **input):
            return super(MyMutation, cls).mutate_and_get_payload(root, info, **input)

Connection example:

.. code:: python
    import graphene
    from graphene_django.fields import DjangoConnectionField
    from graphene_django.auth import connection_require_permission, node_require_permission
    from graphene_django.types import DjangoObjectType
    from .models import Reporter

    class ReporterType(DjangoObjectType):

        class Meta:
            model = Reporter
            interfaces = (Node, )

        @classmethod
        @node_require_permission(permissions=('can_view_report',, 'can_edit_foo', ))
        def get_node(cls, info, id):
            return super(ReporterType, cls).get_node(info, id)

    class MyAuthDjangoConnectionField(DjangoConnectionField):

        @classmethod
        @connection_require_permission(permissions=('can_view_foo', ))
        def connection_resolver(cls, resolver, connection, default_manager, max_limit,
                                enforce_first_or_last, root, info, **args):
            return super(MyAuthDjangoConnectionField, cls).connection_resolver(
                resolver, connection, default_manager, max_limit,
                enforce_first_or_last, root, info, **args)

    class Query(graphene.ObjectType):
        all_reporters = MyAuthDjangoConnectionField(ReporterType)



Adding login required
---------------------

If you want to use the standard Django LoginRequiredMixin_ you can create your own view, which includes the ``LoginRequiredMixin`` and subclasses the ``GraphQLView``:

.. code:: python

    from django.contrib.auth.mixins import LoginRequiredMixin
    from graphene_django.views import GraphQLView


    class PrivateGraphQLView(LoginRequiredMixin, GraphQLView):
        pass

After this, you can use the new ``PrivateGraphQLView`` in ``urls.py``:

.. code:: python

    urlpatterns = [
      # some other urls
      url(r'^graphql', PrivateGraphQLView.as_view(graphiql=True, schema=schema)),
    ]

.. _LoginRequiredMixin: https://docs.djangoproject.com/en/1.10/topics/auth/default/#the-loginrequired-mixin
