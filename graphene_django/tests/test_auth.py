import collections
import graphene
import pytest
from graphene import Schema, relay, ObjectType
from django.test import TestCase, RequestFactory
from graphene_django import DjangoObjectType
from graphene_django.auth.mixins import AuthNodeMixin, AuthMutationMixin
from django.core.exceptions import PermissionDenied
from .models import Pet

from graphene_django.utils import DJANGO_FILTER_INSTALLED

pytestmark = []

if DJANGO_FILTER_INSTALLED:
    from graphene_django.auth.fields import AuthDjangoFilterConnectionField
else:
    pytestmark.append(pytest.mark.skipif(True, reason='django_filters not installed'))

pytestmark.append(pytest.mark.django_db)


class PetNode(AuthNodeMixin, DjangoObjectType):
    _permission = 'app.view_pet'

    class Meta:
        model = Pet
        interfaces = (relay.Node, )


class PetNodeMultiplePermissions(AuthNodeMixin, DjangoObjectType):
    _permission = ('app.view_pet', 'app.add_pet')

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


class CreatePetMultiple(AuthMutationMixin, graphene.Mutation):
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
    _permission = ('app.view_pet', 'app.add_pet')
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


class PetFilterConnection(AuthDjangoFilterConnectionField):
    _permission = 'app.create_pet'


class PetFilterConnectionMultiple(AuthDjangoFilterConnectionField):
    _permission = ('app.view_pet', 'app.add_pet')


class QueryRoot(ObjectType):
    pet = relay.Node.Field(PetNode)
    pets = PetFilterConnection(PetNode)


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
        cls.query_filter = '''
            query {
              pets{
                edges{
                    node{
                        id
                        name
                    }
                }
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
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_query_has_permission(self):
        """
        Making query with an user who has the permission
        """
        result = self.schema.execute(self.query_node, context_value={'user': self.luke})
        self.assertEqual(result.errors, [])

    def test_filter_has_permission(self):
        """
        Making query with an user who has the permission
        """
        result = self.schema.execute(self.query_filter, context_value={'user': self.luke})
        print(result.data)
        print(result.errors)
        self.assertEqual(result.errors, [])

    def test_filter_non_permission(self):
        """
        Making query with an user who has the permission
        """
        result = self.schema.execute(self.query_filter, context_value={'user': self.storm_tropper})
        print(result.data)
        print(result.errors)
        self.assertNotEqual(result.errors, [])
        self.assertEqual(result.errors[0].message, 'Permission Denied')

    def test_auth_node(self):
        pn = PetNode()
        result = pn.get_node(id=1, context=None, info=None)
        assert isinstance(result, PermissionDenied)
        result = pn.get_node(id=1, context={'user': None}, info=None)
        assert isinstance(result, PermissionDenied)
        Context = collections.namedtuple('Context', ['user', ])
        context = Context(MockUserContext(authenticated=False))
        result = pn.get_node(id=1, context=context, info=None)
        assert isinstance(result, PermissionDenied)
        pn_multiple = PetNodeMultiplePermissions()
        context = Context(MockUserContext(authenticated=True))
        result = pn_multiple.get_node(id=1, context=context, info=None)
        assert isinstance(result, PermissionDenied)
        pn_multiple = PetNodeMultiplePermissions()
        context = Context(MockUserContext(authenticated=True))
        result = pn_multiple.get_node(id=10, context=context, info=None)
        assert result is None

    def test_auth_mutation(self):
        pet_mutation = CreatePet()
        result = pet_mutation.has_permision(context=None)
        assert isinstance(result, PermissionDenied)
        result = pet_mutation.has_permision(context={'user': None})
        assert isinstance(result, PermissionDenied)
        Context = collections.namedtuple('Context', ['user', ])
        context = Context(MockUserContext(authenticated=False))
        result = pet_mutation.has_permision(context=context)
        assert isinstance(result, PermissionDenied)
        pet_mutation_multiple = CreatePetMultiple()
        context = Context(MockUserContext(authenticated=True))
        result = pet_mutation_multiple.has_permision(context=context)
        assert isinstance(result, PermissionDenied)
        pet_mutation_multiple = CreatePetMultiple()
        context = Context(MockUserContext(authenticated=True, perms=('app.view_pet', 'app.add_pet')))
        result = pet_mutation_multiple.has_permision(context=context)
        assert result is True

    def test_auth_filter_connection_field(self):
        pet_filter = PetFilterConnection(PetNode)
        result = pet_filter.has_perm(context=None)
        assert result is False
        result = pet_filter.has_perm(context={'user': None})
        assert result is False
        Context = collections.namedtuple('Context', ['user', ])
        context = Context(MockUserContext(authenticated=False))
        result = pet_filter.has_perm(context=context)
        assert result is False
        pet_filter_mulitple = PetFilterConnectionMultiple(PetNode)
        context = Context(MockUserContext(authenticated=True, perms=('app.view_pet', )))
        result = pet_filter_mulitple.has_perm(context=context)
        assert result is False
