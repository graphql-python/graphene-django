# ![Graphene Logo](http://graphene-python.org/favicon.png) Graphene-Django


A [Django](https://www.djangoproject.com/) integration for [Graphene](http://graphene-python.org/).

[![build][build-image]][build-url]
[![pypi][pypi-image]][pypi-url]
[![Anaconda-Server Badge][conda-image]][conda-url]
[![coveralls][coveralls-image]][coveralls-url]

[build-image]: https://github.com/graphql-python/graphene-django/workflows/Tests/badge.svg
[build-url]: https://github.com/graphql-python/graphene-django/actions
[pypi-image]: https://img.shields.io/pypi/v/graphene-django.svg?style=flat
[pypi-url]: https://pypi.org/project/graphene-django/
[coveralls-image]: https://coveralls.io/repos/github/graphql-python/graphene-django/badge.svg?branch=master
[coveralls-url]: https://coveralls.io/github/graphql-python/graphene-django?branch=master
[conda-image]: https://img.shields.io/conda/vn/conda-forge/graphene-django.svg
[conda-url]: https://anaconda.org/conda-forge/graphene-django

[💬 Join the community on Slack](https://join.slack.com/t/graphenetools/shared_invite/enQtOTE2MDQ1NTg4MDM1LTA4Nzk0MGU0NGEwNzUxZGNjNDQ4ZjAwNDJjMjY0OGE1ZDgxZTg4YjM2ZTc4MjE2ZTAzZjE2ZThhZTQzZTkyMmM)

## Documentation

[Visit the documentation to get started!](https://docs.graphene-python.org/projects/django/en/latest/)

## Quickstart

For installing graphene, just run this command in your shell

```bash
pip install "graphene-django>=3"
```

### Settings

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
from django.urls import path
from graphene_django.views import GraphQLView

urlpatterns = [
    # ...
    path('graphql/', GraphQLView.as_view(graphiql=True)),
]
```

## Examples

Here is a simple Django model:

```python
from django.db import models

class UserModel(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
```

To create a GraphQL schema for it you simply have to write the following:

```python
from graphene_django import DjangoObjectType
import graphene

class User(DjangoObjectType):
    class Meta:
        model = UserModel

class Query(graphene.ObjectType):
    users = graphene.List(User)

    def resolve_users(self, info):
        return UserModel.objects.all()

schema = graphene.Schema(query=Query)
```

Then you can query the schema:

```python
query = '''
    query {
      users {
        name,
        lastName
      }
    }
'''
result = schema.execute(query)
```

To learn more check out the following [examples](examples/):

* **Schema with Filtering**: [Cookbook example](examples/cookbook)
* **Relay Schema**: [Starwars Relay example](examples/starwars)


## GraphQL testing clients
 - [Firecamp](https://firecamp.io/graphql)
 - [GraphiQL](https://github.com/graphql/graphiql)


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Release Notes

* See [Releases page on github](https://github.com/graphql-python/graphene-django/releases)
