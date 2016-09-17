You are in the `next` unreleased version of Graphene-Django (`1.0.dev`).
Please read [UPGRADE-v1.0.md](https://github.com/graphql-python/graphene/blob/master/UPGRADE-v1.0.md) to learn how to upgrade.

---

# ![Graphene Logo](http://graphene-python.org/favicon.png) [Graphene-Django](http://graphene-python.org) [![Build Status](https://travis-ci.org/graphql-python/graphene-django.svg?branch=master)](https://travis-ci.org/graphql-python/graphene-django) [![PyPI version](https://badge.fury.io/py/graphene-django.svg)](https://badge.fury.io/py/graphene-django) [![Coverage Status](https://coveralls.io/repos/graphql-python/graphene-django/badge.svg?branch=master&service=github)](https://coveralls.io/github/graphql-python/graphene-django?branch=master)


[Graphene](http://graphene-python.org) is a Python library for building GraphQL schemas/types fast and easily.

- **Easy to use:** Graphene helps you use GraphQL in Python without effort.
- **Relay:** Graphene has builtin support for Relay
- **Django:** Automatic *Django model* mapping to Graphene Types. Check a fully working [Django](http://github.com/graphql-python/swapi-graphene) implementation

Graphene also supports *SQLAlchemy*!

*What is supported in this Python version?* **Everything**: Interfaces, ObjectTypes, Scalars, Unions and Relay (Nodes, Connections), in addition to queries, mutations and subscriptions.

**NEW**!: [Try graphene online](http://graphene-python.org/playground/)

## Installation

For instaling graphene, just run this command in your shell

```bash
pip install "graphene-django>=1.0.dev"
```

## Examples

Here is one example for get you started:

```python
from django.db import models
from graphene_django import DjangoObjectType

class UserModel(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

class User(DjangoObjectType):
    class Meta:
        # This type will transform all the UserModel fields
        # into Graphene fields automatically
        model = UserModel

    # An extra field in the User Type
    full_name = graphene.String()

    def resolve_full_name(self, args, context, info):
        return "{} {}".format(self.name, self.last_name)
```

If you want to learn even more, you can also check the following [examples](examples/):

* **Schema with Filtering**: [Cookbook example](examples/cookbook)
* **Relay Schema**: [Starwars Relay example](examples/starwars)


## Contributing

After cloning this repo, ensure dependencies are installed by running:

```sh
python setup.py install
```

After developing, the full test suite can be evaluated by running:

```sh
python setup.py test # Use --pytest-args="-v -s" for verbose mode
```
