# ![Graphene Logo](http://graphene-python.org/favicon.png) Graphene-Django


A [Django](https://www.djangoproject.com/) integration for [Graphene](http://graphene-python.org/).

[![travis][travis-image]][travis-url]
[![pypi][pypi-image]][pypi-url]
[![Anaconda-Server Badge][conda-image]][conda-url]
[![coveralls][coveralls-image]][coveralls-url]

[travis-image]: https://travis-ci.org/graphql-python/graphene-django.svg?branch=master&style=flat
[travis-url]: https://travis-ci.org/graphql-python/graphene-django
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
pip install "graphene-django>=2.0"
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
    path('graphql', GraphQLView.as_view(graphiql=True)),
]
```

### Subscription Support

The `graphene-django` project does not currently support GraphQL subscriptions out of the box. However, there are
several community-driven modules for adding subscription support, and the GraphiQL interface provided by
`graphene-django` supports subscriptions over websockets.

To implement websocket-based support for GraphQL subscriptions, you'll need to:

1. Install and configure [`django-channels`](https://channels.readthedocs.io/en/latest/installation.html).
2. Install and configure<sup>1, 2</sup> a third-party module for adding subscription support over websockets. A few
   options include:
   - [`graphql-python/graphql-ws`](https://github.com/graphql-python/graphql-ws)
   - [`datavance/django-channels-graphql-ws`](https://github.com/datadvance/DjangoChannelsGraphqlWs)
   - [`jaydenwindle/graphene-subscriptions`](https://github.com/jaydenwindle/graphene-subscriptions)
3. Ensure that your application (or at least your GraphQL endpoint) is being served via an ASGI protocol server like
   `daphne` (built in to `django-channels`), [`uvicorn`](https://www.uvicorn.org/), or
   [`hypercorn`](https://pgjones.gitlab.io/hypercorn/).

> **<sup>1</sup> Note:** By default, the GraphiQL interface that comes with `graphene-django` assumes that you are
> handling subscriptions at the same path as any other operation (i.e., you configured both `urls.py` and `routing.py`
> to handle GraphQL operations at the same path, like `/graphql`).
>
> If these URLs differ, GraphiQL will try to run your subscription over HTTP, which will produce an error. If you need
> to use a different URL for handling websocket connections, you can configure `SUBSCRIPTION_PATH` in your
> `settings.py`:
>
> ```python
> GRAPHENE = {
>     # ...
>     "SUBSCRIPTION_PATH": "/ws/graphql"  # The path you configured in `routing.py`, including a leading slash.
> }
> ```

Once your application is properly configured to handle subscriptions, you can use the GraphiQL interface to test
subscriptions like any other operation.

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


## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Release Notes

* See [Releases page on github](https://github.com/graphql-python/graphene-django/releases)
