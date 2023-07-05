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

To limit fields in a GraphQL query simply use the ``fields`` meta attribute.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            fields = ('title', 'content')
            interfaces = (relay.Node, )

conversely you can use ``exclude`` meta attribute.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            exclude = ('published', 'owner')
            interfaces = (relay.Node, )


Another pattern is to have a resolve method act as a gatekeeper, returning None
or raising an exception if the client isn't allowed to see the data.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            fields = ('title', 'content', 'owner')
            interfaces = (relay.Node, )

        def resolve_owner(self, info):
            user = info.context.user
            if user.is_anonymous:
                raise PermissionDenied("Please login")
            if not user.is_staff:
                return None
            return self.owner


Queryset Filtering On Lists
---------------------------

In order to filter which objects are available in a queryset-based list,
define a resolve method for that field and return the desired queryset.

.. code:: python

    from graphene import ObjectType
    from graphene_django.filter import DjangoFilterConnectionField
    from .models import Post

    class Query(ObjectType):
        all_posts = DjangoFilterConnectionField(PostNode)

        def resolve_all_posts(self, info):
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
        my_posts = DjangoFilterConnectionField(PostNode)

        def resolve_my_posts(self, info):
            # context will reference to the Django request
            if not info.context.user.is_authenticated:
                return Post.objects.none()
            else:
                return Post.objects.filter(owner=info.context.user)

If you're using your own view, passing the request context into the
schema is simple.

.. code:: python

    result = schema.execute(query, context_value=request)


Global Filtering
----------------

If you are using ``DjangoObjectType`` you can define a custom `get_queryset`.

.. code:: python

    from graphene import relay
    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            fields = '__all__'

        @classmethod
        def get_queryset(cls, queryset, info):
            if info.context.user.is_anonymous:
                return queryset.filter(published=True)
            return queryset

.. warning::

    Defining a custom ``get_queryset`` gives the guaranteed it will be called
    when resolving the ``DjangoObjectType``, even through related objects.
    Note that because of this, benefits from using ``select_related``
    in objects that define a relation to this ``DjangoObjectType`` will be canceled out.
    In the case of ``prefetch_related``, the benefits of the optimization will be lost only
    if the custom ``get_queryset`` modifies the queryset. For more information about this, refers
    to Django documentation about ``prefetch_related``: https://docs.djangoproject.com/en/4.2/ref/models/querysets/#prefetch-related.


    If you want to explicitly disable the execution of the custom ``get_queryset`` when resolving,
    you can decorate the resolver with `@graphene_django.bypass_get_queryset`. Note that this
    can lead to authorization leaks if you are performing authorization checks in the custom
    ``get_queryset``.

Filtering ID-based Node Access
------------------------------

In order to add authorization to id-based node access, we need to add a
method to your ``DjangoObjectType``.

.. code:: python

    from graphene_django.types import DjangoObjectType
    from .models import Post

    class PostNode(DjangoObjectType):
        class Meta:
            model = Post
            fields = ('title', 'content')
            interfaces = (relay.Node, )

        @classmethod
        def get_node(cls, info, id):
            try:
                post = cls._meta.model.objects.get(id=id)
            except cls._meta.model.DoesNotExist:
                return None

            if post.published or info.context.user == post.owner:
                return post
            return None


Adding Login Required
---------------------

To restrict users from accessing the GraphQL API page the standard Django LoginRequiredMixin_ can be used to create your own standard Django Class Based View, which includes the ``LoginRequiredMixin`` and subclasses the ``GraphQLView``.:

.. code:: python

    # views.py

    from django.contrib.auth.mixins import LoginRequiredMixin
    from graphene_django.views import GraphQLView


    class PrivateGraphQLView(LoginRequiredMixin, GraphQLView):
        pass

After this, you can use the new ``PrivateGraphQLView`` in the project's URL Configuration file ``url.py``:

For Django 2.2 and above:

.. code:: python

    urlpatterns = [
        # some other urls
        path('graphql/', PrivateGraphQLView.as_view(graphiql=True, schema=schema)),
    ]

.. _LoginRequiredMixin: https://docs.djangoproject.com/en/dev/topics/auth/default/#the-loginrequired-mixin
