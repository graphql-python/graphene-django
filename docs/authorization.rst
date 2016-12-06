Authorization in Django
=======================

There are two main ways you may want to limit access to data when
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

        def resolve_my_posts(self, args, context, info):
            # context will reference to the Django request
            if not context.user.is_authenticated():
                return Post.objects.none()
            else:
                return Post.objects.filter(owner=context.user)

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
