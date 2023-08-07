import graphene
from graphene import Schema, relay, resolve_only_args
from graphene_django import DjangoConnectionField, DjangoObjectType

from .data import create_ship, get_empire, get_faction, get_rebels, get_ship, get_ships
from .models import (
    Character as CharacterModel,
    Faction as FactionModel,
    Ship as ShipModel,
)


class Ship(DjangoObjectType):
    class Meta:
        model = ShipModel
        interfaces = (relay.Node,)
        fields = "__all__"

    @classmethod
    def get_node(cls, info, id):
        node = get_ship(id)
        return node


class Character(DjangoObjectType):
    class Meta:
        model = CharacterModel
        fields = "__all__"


class Faction(DjangoObjectType):
    class Meta:
        model = FactionModel
        interfaces = (relay.Node,)
        fields = "__all__"

    @classmethod
    def get_node(cls, info, id):
        return get_faction(id)


class IntroduceShip(relay.ClientIDMutation):
    class Input:
        ship_name = graphene.String(required=True)
        faction_id = graphene.String(required=True)

    ship = graphene.Field(Ship)
    faction = graphene.Field(Faction)

    @classmethod
    def mutate_and_get_payload(
        cls, root, info, ship_name, faction_id, client_mutation_id=None
    ):
        ship = create_ship(ship_name, faction_id)
        faction = get_faction(faction_id)
        return IntroduceShip(ship=ship, faction=faction)


class Query(graphene.ObjectType):
    rebels = graphene.Field(Faction)
    empire = graphene.Field(Faction)
    node = relay.Node.Field()
    ships = DjangoConnectionField(Ship, description="All the ships.")

    @resolve_only_args
    def resolve_ships(self):
        return get_ships()

    @resolve_only_args
    def resolve_rebels(self):
        return get_rebels()

    @resolve_only_args
    def resolve_empire(self):
        return get_empire()


class Mutation(graphene.ObjectType):
    introduce_ship = IntroduceShip.Field()


# We register the Character Model because if not would be
# inaccessible for the schema
schema = Schema(query=Query, mutation=Mutation, types=[Ship, Character])
