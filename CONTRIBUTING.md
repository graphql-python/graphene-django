# Contributing

Thanks for helping to make graphene-django great!

We welcome all kinds of contributions:

- Bug fixes
- Documentation improvements
- New features
- Refactoring & tidying


## Getting started

If you have a specific contribution in mind, be sure to check the [issues](https://github.com/graphql-python/graphene-django/issues) and [projects](https://github.com/graphql-python/graphene-django/projects) in progress - someone could already be working on something similar and you can help out.


## Project setup

After cloning this repo, ensure dependencies are installed by running:

```sh
make dev-setup
```

## Running tests

After developing, the full test suite can be evaluated by running:

```sh
make tests
```

## Documentation

The [documentation](http://docs.graphene-python.org/projects/django/en/latest/) is generated using the excellent [Sphinx](http://www.sphinx-doc.org/) and a custom theme.

The documentation dependencies are installed by running:

```sh
cd docs
pip install -r requirements.txt
```

Then to produce a HTML version of the documentation:

```sh
make html
```