from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

from cookbook.recipes.models import Recipe, RecipeIngredient


class RecipeNode(DjangoObjectType):
    class Meta:
        model = Recipe
        interfaces = (Node,)
        fields = "__all__"
        filter_fields = ["title", "amounts"]


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
    all_recipes = DjangoFilterConnectionField(RecipeNode)

    recipeingredient = Node.Field(RecipeIngredientNode)
    all_recipeingredients = DjangoFilterConnectionField(RecipeIngredientNode)
