from cookbook.recipes.models import Recipe, RecipeIngredient
from graphene import AbstractType, Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType

class RecipeNode(DjangoObjectType):

    class Meta:
        model = Recipe
        interfaces = (Node, )
        filter_fields = ['title','amounts']
        filter_order_by = ['title']

class RecipeIngredientNode(DjangoObjectType):

    class Meta:
        model = RecipeIngredient
        # Allow for some more advanced filtering here
        interfaces = (Node, )
        filter_fields = {
            'ingredient__name': ['exact', 'icontains', 'istartswith'],
            'recipe': ['exact'],
            'recipe__title': ['icontains'],
        }
        filter_order_by = ['ingredient__name', 'recipe__title',]

class Query(AbstractType):
    recipe = Node.Field(RecipeNode)
    all_recipes = DjangoFilterConnectionField(RecipeNode)

    recipeingredient = Node.Field(RecipeIngredientNode)
    all_recipeingredients = DjangoFilterConnectionField(RecipeIngredientNode)
