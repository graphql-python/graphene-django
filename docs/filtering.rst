Filtering
=========

Graphene-Django integrates with
`django-filter <https://django-filter.readthedocs.io/en/master/>`__ (2.x for
Python 3 or 1.x for Python 2) to provide filtering of results. See the `usage
documentation <https://django-filter.readthedocs.io/en/master/guide/usage.html#the-filter>`__
for details on the format for ``filter_fields``.

This filtering is automatically available when implementing a ``relay.Node``.
Additionally ``django-filter`` is an optional dependency of Graphene.

You will need to install it manually, which can be done as follows:

.. code:: bash

    # You'll need to install django-filter
    pip install django-filter>=2
    
After installing ``django-filter`` you'll need to add the application in the ``settings.py`` file:

.. code:: python

    INSTALLED_APPS = [
        # ...
        "django_filters",
    ]

Note: The techniques below are demoed in the `cookbook example
app <https://github.com/graphql-python/graphene-django/tree/master/examples/cookbook>`__.

Filterable fields
-----------------

The ``filter_fields`` parameter is used to specify the fields which can
be filtered upon. The value specified here is passed directly to
``django-filter``, so see the `filtering
documentation <https://django-filter.readthedocs.io/en/master/guide/usage.html#the-filter>`__
for full details on the range of options available.

For example:

.. code:: python

    class AnimalNode(DjangoObjectType):
        class Meta:
            # Assume you have an Animal model defined with the following fields
            model = Animal
            filter_fields = ['name', 'genus', 'is_domesticated']
            interfaces = (relay.Node, )

    class Query(ObjectType):
        animal = relay.Node.Field(AnimalNode)
        all_animals = DjangoFilterConnectionField(AnimalNode)

You could then perform a query such as:

.. code::

    query {
      # Note that fields names become camelcased
      allAnimals(genus: "cat", isDomesticated: true) {
        edges {
          node {
            id,
            name
          }
        }
      }
    }

You can also make more complex lookup types available:

.. code:: python

    class AnimalNode(DjangoObjectType):
        class Meta:
            model = Animal
            # Provide more complex lookup types
            filter_fields = {
                'name': ['exact', 'icontains', 'istartswith'],
                'genus': ['exact'],
                'is_domesticated': ['exact'],
            }
            interfaces = (relay.Node, )

Which you could query as follows:

.. code::

    query {
      # Note that fields names become camelcased
      allAnimals(name_Icontains: "lion") {
        edges {
          node {
            id,
            name
          }
        }
      }
    }

Custom Filtersets
-----------------

By default Graphene provides easy access to the most commonly used
features of ``django-filter``. This is done by transparently creating a
``django_filters.FilterSet`` class for you and passing in the values for
``filter_fields``.

However, you may find this to be insufficient. In these cases you can
create your own ``FilterSet``. You can pass it directly as follows:

.. code:: python

    class AnimalNode(DjangoObjectType):
        class Meta:
            # Assume you have an Animal model defined with the following fields
            model = Animal
            filter_fields = ['name', 'genus', 'is_domesticated']
            interfaces = (relay.Node, )


    class AnimalFilter(django_filters.FilterSet):
        # Do case-insensitive lookups on 'name'
        name = django_filters.CharFilter(lookup_expr=['iexact'])

        class Meta:
            model = Animal
            fields = ['name', 'genus', 'is_domesticated']


    class Query(ObjectType):
        animal = relay.Node.Field(AnimalNode)
        # We specify our custom AnimalFilter using the filterset_class param
        all_animals = DjangoFilterConnectionField(AnimalNode,
                                                  filterset_class=AnimalFilter)

You can also specify the ``FilterSet`` class using the ``filterset_class``
parameter when defining your ``DjangoObjectType``, however, this can't be used
in unison  with the ``filter_fields`` parameter:

.. code:: python

    class AnimalFilter(django_filters.FilterSet):
        # Do case-insensitive lookups on 'name'
        name = django_filters.CharFilter(lookup_expr=['iexact'])

        class Meta:
            # Assume you have an Animal model defined with the following fields
            model = Animal
            fields = ['name', 'genus', 'is_domesticated']


    class AnimalNode(DjangoObjectType):
        class Meta:
            model = Animal
            filterset_class = AnimalFilter
            interfaces = (relay.Node, )


    class Query(ObjectType):
        animal = relay.Node.Field(AnimalNode)
        all_animals = DjangoFilterConnectionField(AnimalNode)

The context argument is passed on as the `request argument <http://django-filter.readthedocs.io/en/master/guide/usage.html#request-based-filtering>`__
in a ``django_filters.FilterSet`` instance. You can use this to customize your
filters to be context-dependent. We could modify the ``AnimalFilter`` above to
pre-filter animals owned by the authenticated user (set in ``context.user``).

.. code:: python

    class AnimalFilter(django_filters.FilterSet):
        # Do case-insensitive lookups on 'name'
        name = django_filters.CharFilter(lookup_type=['iexact'])

        class Meta:
            model = Animal
            fields = ['name', 'genus', 'is_domesticated']

        @property
        def qs(self):
            # The query context can be found in self.request.
            return super(AnimalFilter, self).qs.filter(owner=self.request.user)


Ordering
--------

You can use ``OrderFilter`` to define how you want your returned results to be ordered.

Extend the tuple of fields if you want to order by more than one field.

.. code:: python

    from django_filters import FilterSet, OrderingFilter

    class UserFilter(FilterSet):
        class Meta:
            model = UserModel

        order_by = OrderingFilter(
            fields=(
                ('name', 'created_at'),
            )
        )

    class Group(DjangoObjectType):
      users = DjangoFilterConnectionField(Ticket, filterset_class=UserFilter)

      class Meta:
          name = 'Group'
          model = GroupModel
          interfaces = (relay.Node,)

      def resolve_users(self, info, **kwargs):
        return UserFilter(kwargs).qs


with this set up, you can now order the users under group:

.. code::

    query {
      group(id: "xxx") {
        users(orderBy: "-created_at") {
          xxx
        }
      }
    }
