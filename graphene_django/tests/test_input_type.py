from mock import patch

from graphene import ObjectType, Schema, Mutation, String

from .. import registry
from ..input_types import DjangoModelInput

from .models import Reporter as ReporterModel


def test_mutation_execution_with_exclude_fields():
    registry.reset_global_registry()

    class CreateReporter(Mutation):

        first_name = String()
        last_name = String()
        email = String()

        class Input(DjangoModelInput):

            class Meta:
                model = ReporterModel
                exclude_fields = ('id', 'pets', 'a_choice', 'films', 'articles')

        def mutate(self, args, context, info):
            first_name = args.get('first_name')
            last_name = args.get('last_name')
            email = args.get('email')
            return CreateReporter(first_name=first_name, last_name=last_name, email=email)

    class MyMutation(ObjectType):
        reporter_input = CreateReporter.Field()

    class Query(ObjectType):
        a = String()

    schema = Schema(query=Query, mutation=MyMutation)
    result = schema.execute(''' mutation mymutation {
        reporterInput(firstName:"Peter", lastName: "test", email: "test@test.com") {
            firstName
            lastName
            email
        }
    }
    ''')
    assert not result.errors
    assert result.data == {
        'reporterInput': {
            'firstName': 'Peter',
            'lastName': 'test',
            'email': "test@test.com"
        }
    }


def test_mutation_execution():
    registry.reset_global_registry()

    class ReporterInput(Mutation):

        first_name = String()
        last_name = String()

        class Input(DjangoModelInput):

            class Meta:
                model = ReporterModel
                only_fields = ('first_name', 'last_name')

        def mutate(self, args, context, info):
            first_name = args.get('first_name')
            last_name = args.get('last_name')
            return ReporterInput(first_name=first_name, last_name=last_name)

    class MyMutation(ObjectType):
        reporter_input = ReporterInput.Field()

    class Query(ObjectType):
        a = String()

    schema = Schema(query=Query, mutation=MyMutation)
    result = schema.execute(''' mutation mymutation {
        reporterInput(firstName:"Peter", lastName: "test") {
            firstName
            lastName
        }
    }
    ''')
    assert not result.errors
    assert result.data == {
        'reporterInput': {
            'firstName': 'Peter',
            'lastName': 'test',
        }
    }
