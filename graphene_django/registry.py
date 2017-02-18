class Registry(object):

    def __init__(self):
        self._registry = {}
        self._registry_models = {}

    def register(self, cls):
        from .types import DjangoObjectType
        model = cls._meta.model
        assert self._registry.get(model, cls) == cls, (
            'Django Model "{}.{}" already associated with {}. '
            'You can use a different registry for {} or skip '
            'the global Registry with "{}.Meta.skip_global_registry = True".'
        ).format(
            model._meta.app_label,
            model._meta.object_name,
            repr(self.get_type_for_model(cls._meta.model)),
            repr(cls),
            cls
        )
        assert issubclass(
            cls, DjangoObjectType), 'Only DjangoObjectTypes can be registered, received "{}"'.format(
            cls.__name__)
        assert cls._meta.registry == self, 'Registry for a Model have to match.'
        self._registry[cls._meta.model] = cls

    def get_type_for_model(self, model):
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
