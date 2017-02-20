from collections import defaultdict


class Registry(object):

    def __init__(self):
        self._registry = defaultdict(list)

    def register(self, cls):
        from .types import DjangoObjectType
        model = cls._meta.model
        assert issubclass(
            cls, DjangoObjectType), 'Only DjangoObjectTypes can be registered, received "{}"'.format(
            cls.__name__)
        assert cls._meta.registry == self, 'Registry for a Model have to match.'
        self._registry[model].append(cls)

    def get_unique_type_for_model(self, model):
        types = self.get_types_for_model(model)
        if not types:
            return None

        # If there is more than one type for the model, we should
        # raise an error so both types don't collide in the same schema.
        assert len(types) == 1, (
            'Found multiple ObjectTypes associated with the same Django Model "{}.{}": {}. '
            'You can use a different registry for each or skip '
            'the global Registry with Meta.skip_global_registry = True". '
            'Read more at http://docs.graphene-python.org/projects/django/en/latest/registry/ .'
        ).format(
            model._meta.app_label,
            model._meta.object_name,
            repr(types),
        )
        return types[0]

    def get_types_for_model(self, model):
        return self._registry.get(model)


registry = None


def get_global_registry():
    global registry
    if not registry:
        registry = Registry()
    return registry


def reset_global_registry():
    global registry
    registry = None
