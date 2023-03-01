import graphene
from graphene_django.types import DjangoObjectType

from .models import Recipe, RecipeIngredient


class RecipeType(DjangoObjectType):
    class Meta:
        model = Recipe
        fields = "__all__"


class RecipeIngredientType(DjangoObjectType):
    class Meta:
        model = RecipeIngredient
        fields = "__all__"


class Query:
    recipe = graphene.Field(RecipeType, id=graphene.Int(), title=graphene.String())
    all_recipes = graphene.List(RecipeType)

    recipeingredient = graphene.Field(RecipeIngredientType, id=graphene.Int())
    all_recipeingredients = graphene.List(RecipeIngredientType)

    def resolve_recipe(self, context, id=None, title=None):
        if id is not None:
            return Recipe.objects.get(pk=id)

        if title is not None:
            return Recipe.objects.get(title=title)

        return None

    def resolve_recipeingredient(self, context, id=None):
        if id is not None:
            return RecipeIngredient.objects.get(pk=id)

        return None

    def resolve_all_recipes(self, context):
        return Recipe.objects.all()

    def resolve_all_recipeingredients(self, context):
        related = ["recipe", "ingredient"]
        return RecipeIngredient.objects.select_related(*related).all()
