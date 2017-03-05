import graphene
from graphene import Schema, relay, ObjectType
from ..filter import DjangoFilterConnectionField
from django.test import TestCase, RequestFactory
from ..types import DjangoObjectType
from .models import Pet
from ..auth.mixins import AuthNodeMixin, AuthMutationMixin


class PetNode(AuthNodeMixin, DjangoObjectType):
    _permission = 'app.view_pet'

    class Meta:
        model = Pet
        interfaces = (relay.Node, )


class CreatePet(AuthMutationMixin, graphene.Mutation):
    """
    Mutation for create user
    example mutation:
        mutation {
            createPet(name: "Mila") {
                pet {
                    id
                    name
                }
            }
        }
    """
    _permission = 'app.create_pet'
    pet = graphene.Field(PetNode)

    class Input:
        name = graphene.String(required=True)

    @classmethod
    def mutate(cls, root, input, context, info):
        if cls.has_permision(context) is not True:
            return cls.has_permision(context)
        pet_name = input.get('name')
        pet = Pet.objects.create(name=pet_name)
        return CreatePet(pet=pet)


class QueryRoot(ObjectType):
    pet = relay.Node.Field(PetNode)
    pets = DjangoFilterConnectionField(PetNode)


class MutationRoot(ObjectType):
    create_pet = CreatePet.Field()

schema = Schema(query=QueryRoot, mutation=MutationRoot)


class MockUserContext(object):

    def __init__(self, authenticated=True, is_staff=False, superuser=False, perms=()):
        self.user = self
        self.authenticated = authenticated
        self.is_staff = is_staff
        self.is_superuser = superuser
        self.perms = perms

    def is_authenticated(self):
        return self.authenticated

    def has_perm(self, check_perms):
        if check_perms not in self.perms:
            return False
        return True


class AuthorizationTests(TestCase):
    """
    This TestCase auth.
    """

    @classmethod
    def setUpClass(cls):
        super(AuthorizationTests, cls).setUpClass()
        cls.schema = schema
        cls.query_mutation = '''
            mutation {{
                createPet(name: "{name}") {{
                    pet{{
                        id
                        name
                    }}
                }}
            }}
        '''
        cls.query_node = '''
            query {
              pet(id: "UGV0Tm9kZTox"){
                id
                name
              }
            }
        '''

    def setUp(self):
        self.factory = RequestFactory()
        pet_names = ['Mila', 'Kira']
        for name in pet_names:
            Pet.objects.create(name=name)
        self.anonymous = MockUserContext(
            authenticated=False
        )
        self.luke = MockUserContext(
            authenticated=True,
            perms=('app.view_pet', 'app.create_pet',)
        )
        self.anakin = MockUserContext(
            authenticated=True,
            perms=('app.view_pet',)
        )
        self.storm_tropper = MockUserContext(
            authenticated=True,
            perms=()
        )

    def test_mutation_anonymous(self):
        """
        Making mutation with anonymous user
        """
        print(self.luke.user)
        result = self.schema.execute(self.query_mutation.format(name='Mila'), context_value={'user': self.anonymous})
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_mutation_non_permission(self):
        """
        Making mutation with an user who does not have the permission
        """
        result = self.schema.execute(self.query_mutation.format(name='Mila'), context_value={'user': self.anakin})
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_mutation_has_permission(self):
        """
        Making mutation with an user who has the permission
        """
        result = self.schema.execute(self.query_mutation.format(name='Mila'), context_value={'user': self.luke})
        self.assertEqual(result.errors, [])

    def test_query_anonymous(self):
        """
        Making query with anonymous user
        """
        result = self.schema.execute(self.query_node, context_value={'user': self.anonymous})
        print(result.errors)
        print(result.data)
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_query_non_permission(self):
        """
        Making query with an user who does not have the permission
        """
        result = self.schema.execute(self.query_node, context_value={'user': self.storm_tropper})
        print(result.errors)
        print(result.data)
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_query_has_permission(self):
        """
        Making query with an user who has the permission
        """
        result = self.schema.execute(self.query_node, context_value={'user': self.luke})
        print(result.errors)
        print(result.data)
        self.assertEqual(result.errors, [])
