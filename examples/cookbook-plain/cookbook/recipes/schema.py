import graphene
from graphene_django.types import DjangoObjectType

from .models import Recipe, RecipeIngredient


class RecipeType(DjangoObjectType):
    class Meta:
        model = Recipe


class RecipeIngredientType(DjangoObjectType):
    class Meta:
        model = RecipeIngredient


class Query(object):
    recipe = graphene.Field(RecipeType,
                            id=graphene.Int(),
                            title=graphene.String())
    all_recipes = graphene.List(RecipeType)

    recipeingredient = graphene.Field(RecipeIngredientType,
                                      id=graphene.Int())
    all_recipeingredients = graphene.List(RecipeIngredientType)

    def resolve_recipe(self, context, **kwargs):
        id = kwargs.get('id')
        title = kwargs.get('title')

        if id is not None:
            return Recipe.objects.get(pk=id)

        if title is not None:
            return Recipe.objects.get(title=title)

        return None

    def resolve_recipeingredient(self, context, **kwargs):
        id = kwargs.get('id')

        if id is not None:
            return RecipeIngredient.objects.get(pk=id)

        return None

    def resolve_all_recipes(self, context, **kwargs):
        return Recipe.objects.all()

    def resolve_all_recipeingredients(self, context, **kwargs):
        related = ['recipe', 'ingredient']
        return RecipeIngredient.objects.select_related(*related).all()
