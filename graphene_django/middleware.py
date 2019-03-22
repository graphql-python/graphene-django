import six
from graphql import DirectiveLocation, GraphQLDirective
from promise import Promise

class DirectivesMiddleware(object):

    def resolve(self, next, root, info, **kwargs):
        result = next(root, info, **kwargs)
        return result.then(
            lambda resolved: self.__process_value(resolved, root, info, **kwargs),
            lambda error: Promise.rejected(error)
        )

    def __process_value(self, value, root, info, **kwargs):
        field = info.field_asts[0]
        # if field has not directive - return model-value
        if not field.directives:
            return value
        new_value = value
        # for each by field.directives
        for directive in field.directives:
            directive_class = CustomDirectiveMeta.REGISTRY.get(directive.name.value)
            if directive_class:
                # if directive class found
                new_value = directive_class.process(new_value, directive, root, info, **kwargs)
        return new_value


class CustomDirectiveMeta(type):
    REGISTRY = {}

    def __new__(mcs, name, bases, attrs):
        newclass = super(CustomDirectiveMeta, mcs).__new__(mcs, name, bases, attrs)
        if name != 'BaseCustomDirective':
            mcs.register(newclass)
        return newclass

    @classmethod
    def register(mcs, target):
        mcs.REGISTRY[target.get_name()] = target

    @classmethod
    def get_all_directives(cls):
        return [d() for d in cls.REGISTRY.values()]


class BaseCustomDirective(six.with_metaclass(CustomDirectiveMeta, GraphQLDirective)):
    __metaclass__ = CustomDirectiveMeta

    def __init__(self):
        super(BaseCustomDirective, self).__init__(
            name=self.get_name(),
            description=self.__doc__,
            args=self.get_args(),
            locations=[
                DirectiveLocation.FIELD
            ]
        )

    @classmethod
    def get_name(cls):
        return cls.__name__.replace('Directive', '').lower()

    @staticmethod
    def get_args():
        return {}

from .directives import * # define the directives
