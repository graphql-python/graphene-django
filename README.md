Please read [UPGRADE-v2.0.md](https://github.com/graphql-python/graphene/blob/master/UPGRADE-v2.0.md) to learn how to upgrade to Graphene `2.0`.

---

# ![Graphene Logo](http://graphene-python.org/favicon.png) Graphene-Neo4j [![Build Status](https://travis-ci.org/graphql-python/graphene-django.svg?branch=master)](https://travis-ci.org/graphql-python/graphene-django) [![PyPI version](https://badge.fury.io/py/graphene-django.svg)](https://badge.fury.io/py/graphene-django) [![Coverage Status](https://coveralls.io/repos/graphql-python/graphene-django/badge.svg?branch=master&service=github)](https://coveralls.io/github/graphql-python/graphene-django?branch=master)


A [Django](https://www.djangoproject.com/) integration for [Graphene](http://graphene-python.org/).

## Documentation

[Visit the documentation to get started!](https://docs.graphene-python.org/projects/django/en/latest/)

## Quickstart

For installing graphene, just run this command in your shell

```bash
pip install "graphene-neo4j>=2.0"
```

### Settings

Use basic graphene_django package in INSTALLED_APPS

```python
INSTALLED_APPS = (
    # ...
    'django.contrib.staticfiles', # Required for GraphiQL
    'graphene_django',
)

GRAPHENE = {
    'SCHEMA': 'app.schema.schema' # Where your Graphene schema lives
}
```

### Urls

We need to set up a `GraphQL` endpoint in our Django app, so we can serve the queries.

```python
from django.conf.urls import url
from graphene_django.views import GraphQLView

urlpatterns = [
    # ...
    url(r'^graphql$', GraphQLView.as_view(graphiql=True)),
]
```

## Examples

Here is a simple neomodel model:

```python
from neomodel import *

class UserModel(StructuredNode):
    name = StringProperty(required=True)
    age = IntegerProperty()
```

To create a GraphQL schema for it you simply have to write the following:

```python
from graphene_django import DjangoObjectType
import graphene

class User(DjangoObjectType):
    class Meta:
        # pass yours model here, the fields are define automatically
        model = UserModel

class Query(graphene.ObjectType):
    users = graphene.List(User)

    def resolve_users(self, info):
        return UserModel.nodes.all()

schema = graphene.Schema(query=Query)
```


### Relay schema

```python
import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter.fields import DjangoFilterConnectionField

class UserType(DjangoObjectType):
    class Meta:
        # pass yours model here, the fields are define automatically
        model = UserModel

        # definition of filter settings
        # key - the <field_name>
        # value - the list of search instructions
        neomodel_filter_fields = {
            'name': ['icontains', 'contains', 'exact'],
            'age': ['lte', 'gte', 'gt'],
        }

        interfaces = (
            graphene.relay.Node,
        )

class Query(graphene.ObjectType):
    """ The types resolves automatically
    """
    user = graphene.relay.Node.Field(UserType)
    users = DjangoFilterConnectionField(UserType)


schema = graphene.Schema(query=Query)
```


Then you can simply query the schema:

```python
query = '''
    query {
      users {
        name
        age
      }
    }
'''
result = schema.execute(query)
```

To learn more check out the following [examples](examples/):

* **Schema with Filtering**: [Cookbook example](examples/cookbook)
* **Relay Schema**: [Starwars Relay example](examples/starwars)
