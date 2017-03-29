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

Adding permissions to Nodes
---------------------------
If you want to user the auth django permissions to access a node, we need to inheritance
from ``AuthNodeMixin`` and define a required permissions in the node. This will return
a ``PermissionDenied`` is the user does not have the required permissions.

.. code:: python

    from graphene_django.types import DjangoObjectType
    from graphene_django.auth.mixins import AuthNodeMixin
    from .models import Post

    class PostNode(AuthNodeMixin, DjangoObjectType):
        _permission = 'app.add_post'

        class Meta:
            model = Post
            only_fields = ('title', 'content')
            interfaces = (relay.Node, )

We can set multiple required permissions like this:

.. code:: python

    from graphene_django.types import DjangoObjectType
    from graphene_django.auth.mixins import AuthNodeMixin
    from .models import Post

    class PostNode(AuthNodeMixin, DjangoObjectType):
        _permission = ('app.add_post', 'app.delete_post',)

        class Meta:
            model = Post
            only_fields = ('title', 'content')
            interfaces = (relay.Node, )

Adding permissions to Mutations
---------------------------
If you want to user the auth django permissions to execute a mutation, we need to inheritance
from ``AuthMutationMixin`` and define a required permissions in the node. This will return
a ``PermissionDenied`` is the user does not have the required permissions.

.. code:: python

    class CreatePet(AuthMutationMixin, graphene.Mutation):
        _permission = 'app.create_pet'
        pet = graphene.Field(PetNode)

        class Input:
            name = graphene.String(required=True)

        @classmethod
        def mutate(cls, root, input, context, info):
            # Auth Required Virification
            if cls.has_permision(context) is not True:
                return cls.has_permision(context)
            # End Auth
            pet_name = input.get('name')
            pet = Pet.objects.create(name=pet_name)
            return CreatePet(pet=pet)

We can set multiple required permissions like this:

.. code:: python

    class CreatePet(AuthMutationMixin, graphene.Mutation):
        _permission = ('app.add_pet', 'app.delete_pet')
        pet = graphene.Field(PetNode)

        class Input:
            name = graphene.String(required=True)

        @classmethod
        def mutate(cls, root, input, context, info):
            # Auth Required Virification
            if cls.has_permision(context) is not True:
                return cls.has_permision(context)
            # End Auth
            pet_name = input.get('name')
            pet = Pet.objects.create(name=pet_name)
            return CreatePet(pet=pet)

Adding permissions to filters
-----------------------------
We use DjangoFilterConnectionField to create filters to our nodes. Graphene-django has a field with
permission required ``AuthDjangoFilterConnectionField``. This field requires permissions to access
to it's nodes and is simple to create your filters.

.. code:: python

    class MyCustomFilter(AuthDjangoFilterConnectionField):
        _permission = ('app.add_pet', 'app.delete_pet')

With this example code we can implement filters with required permissions.
