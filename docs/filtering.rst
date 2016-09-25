Filtering
=========

Graphene integrates with
`django-filter <https://django-filter.readthedocs.org>`__ to provide
filtering of results. See the `usage
documentation <https://django-filter.readthedocs.org/en/latest/usage.html#the-filter>`__
for details on the format for ``filter_fields``.

This filtering is automatically available when implementing a ``relay.Node``.
Additionally ``django-filter`` is an optional dependency of Graphene.

You will need to install it manually, which can be done as follows:

.. code:: bash

    # You'll need to django-filter
    pip install django-filter

Note: The techniques below are demoed in the `cookbook example
app <https://github.com/graphql-python/graphene-django/tree/master/examples/cookbook>`__.

Filterable fields
-----------------

The ``filter_fields`` parameter is used to specify the fields which can
be filtered upon. The value specified here is passed directly to
``django-filter``, so see the `filtering
documentation <https://django-filter.readthedocs.org/en/latest/usage.html#the-filter>`__
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

.. code:: graphql

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

.. code:: graphql

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

Orderable fields
----------------

Ordering can also be specified using ``filter_order_by``. Like
``filter_fields``, this value is also passed directly to
``django-filter`` as the ``order_by`` field. For full details see the
`order\_by
documentation <https://django-filter.readthedocs.org/en/latest/usage.html#ordering-using-order-by>`__.

For example:

.. code:: python

    class AnimalNode(DjangoObjectType):
        class Meta:
            model = Animal
            filter_fields = ['name', 'genus', 'is_domesticated']
            # Either a tuple/list of fields upon which ordering is allowed, or
            # True to allow filtering on all fields specified in filter_fields
            filter_order_by = True
            interfaces = (relay.Node, )

You can then control the ordering via the ``orderBy`` argument:

.. code:: graphql

    query {
      allAnimals(orderBy: "name") {
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
``filter_fields`` and ``filter_order_by``.

However, you may find this to be insufficient. In these cases you can
create your own ``Filterset`` as follows:

.. code:: python

    class AnimalNode(DjangoObjectType):
        class Meta:
            # Assume you have an Animal model defined with the following fields
            model = Animal
            filter_fields = ['name', 'genus', 'is_domesticated']
            interfaces = (relay.Node, )


    class AnimalFilter(django_filters.FilterSet):
        # Do case-insensitive lookups on 'name'
        name = django_filters.CharFilter(lookup_type='iexact')

        class Meta:
            model = Animal
            fields = ['name', 'genus', 'is_domesticated']


    class Query(ObjectType):
        animal = relay.Node.Field(AnimalNode)
        # We specify our custom AnimalFilter using the filterset_class param
        all_animals = DjangoFilterConnectionField(AnimalNode,
                                                  filterset_class=AnimalFilter)
