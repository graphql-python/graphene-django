import asyncio

from asgiref.sync import sync_to_async

from graphene import Field, Node, String
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from cookbook.recipes.models import Recipe, RecipeIngredient


class RecipeNode(DjangoObjectType):
    async_field = String()

    class Meta:
        model = Recipe
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = ["title", "amounts"]

    async def resolve_async_field(self, info):
        await asyncio.sleep(2)
        return "success"


class RecipeType(DjangoObjectType):
    async_field = String()

    class Meta:
        model = Recipe
        fields = "__all__"
        filter_fields = ["title", "amounts"]
        skip_registry = True

    async def resolve_async_field(self, info):
        await asyncio.sleep(2)
        return "success"


class RecipeIngredientNode(DjangoObjectType):
    class Meta:
        model = RecipeIngredient
        # Allow for some more advanced filtering here
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = {
            "ingredient__name": ["exact", "icontains", "istartswith"],
            "recipe": ["exact"],
            "recipe__title": ["icontains"],
        }


class Query:
    recipe = Node.Field(RecipeNode)
    raw_recipe = Field(RecipeType)
    all_recipes = DjangoFilterConnectionField(RecipeNode)

    recipeingredient = Node.Field(RecipeIngredientNode)
    all_recipeingredients = DjangoFilterConnectionField(RecipeIngredientNode)

    @staticmethod
    @sync_to_async
    def resolve_raw_recipe(self, info):
        return Recipe.objects.first()
