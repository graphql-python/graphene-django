import graphene
from graphene_django.types import DjangoObjectType

from cookbook.recipes.models import Recipe, RecipeIngredient


class RecipeType(DjangoObjectType):
    class Meta:
        model = Recipe


class RecipeIngredientType(DjangoObjectType):
    class Meta:
        model = RecipeIngredient


class Query(graphene.AbstractType):
    recipe = graphene.Field(RecipeType,
                            id=graphene.Int(),
                            title=graphene.String())
    all_recipes = graphene.List(RecipeType)

    recipeingredient = graphene.Field(RecipeIngredientType,
                                      id=graphene.Int())
    all_recipeingredients = graphene.List(RecipeIngredientType)

    def resolve_recipe(self, args, context, info):
        id = args.get('id')
        title = args.get('title')

        if id is not None:
            return Recipe.objects.get(pk=id)

        if title is not None:
            return Recipe.objects.get(title=title)

        return None

    def resolve_recipeingredient(self, args, context, info):
        id = args.get('id')

        if id is not None:
            return RecipeIngredient.objects.get(pk=id)

        return None

    def resolve_all_recipes(self, args, context, info):
        return Recipe.objects.all()

    def resolve_all_recipeingredients(self, args, context, info):
        related = ['recipe', 'ingredient']
        return RecipeIngredient.objects.select_related(*related).all()
