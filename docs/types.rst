Types
=====

This page documents specific features of Types related to Graphene-Django.

DjangoChoicesEnum
-----------------

*Introduced in graphene-django 2.3*

``DjangoChoicesEnum`` is a helper class that lets you keep Graphene style enums
and ``models.Field.choices`` in sync. Some Django fields accept a ``choices`` list like this:

.. code:: python

    choices = [
        ('FOO', 'foo'),
        ('BAR', 'bar'),
    ]

    class MyModel(models.Model):
        options = models.CharField(max_length='3', choices=choices)

With Graphene-Django it is useful to represent these choices as an enum:

.. code::

    query getEnumType {
    __type(name: "MyModelOptions" ) {
        name
        enumValues {
                name
                description
            }
        }
    }

Which will return a data structure like this:

.. code::

    {
        "data": {
            "__type": {
            "name": "MyModelOptions",
            "enumValues": [
                {
                    "name": "FOO",
                    "description": "foo"
                },
                {
                    "name": "BAR",
                    "description": "bar"
                }
            ]
            }
        }
    }

We can use ``DjangoChoicesEnum`` to support both of these for us:

.. code:: python

    from graphene_django import DjangoObjectType, DjangoChoicesEnum
    from django.db import models

    # Declare your DjangoChoicesEnum
    class MyModelChoices(DjangoChoicesEnum):
        FOO = 'foo'
        BAR = 'bar'

    # Your model should use the .choices method
    class MyModel(models.Model):
        options = models.CharField(
            max_length='3',
            choices=DjangoChoicesEnum.choices(),
            default=DjangoChoicesEnum.choices()[0][0],
        )

    # And your ObjectType should explicitly declare the type:
    class MyModelType(DjangoObjectType):
        class Meta:
            model = MyModel
            fields = ('options',)

        options = MyModelChoices.as_enum()