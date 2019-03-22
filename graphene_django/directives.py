from .middleware import BaseCustomDirective
from graphql.type.definition import GraphQLArgument, GraphQLNonNull
from graphql.type.scalars import GraphQLString

class DefaultDirective(BaseCustomDirective):
    """
    Default to given value if None
    """
    @staticmethod
    def get_args():
        return {
            'to': GraphQLArgument(
                type=GraphQLNonNull(GraphQLString),
                description='Value to default to',
            ),
        }


    @staticmethod
    def process(value, directive, root, info, **kwargs):
        if value is None:
            to_argument = [arg for arg in directive.arguments if arg.name.value == 'to'][0]
            return to_argument.value.value
        return value
