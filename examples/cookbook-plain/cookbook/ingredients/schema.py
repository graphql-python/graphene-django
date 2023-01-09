import graphene
from graphene_django.types import DjangoObjectType

from .models import Category, Ingredient


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = "__all__"


class IngredientType(DjangoObjectType):
    class Meta:
        model = Ingredient
        fields = "__all__"


class Query:
    category = graphene.Field(CategoryType, id=graphene.Int(), name=graphene.String())
    all_categories = graphene.List(CategoryType)

    ingredient = graphene.Field(
        IngredientType, id=graphene.Int(), name=graphene.String()
    )
    all_ingredients = graphene.List(IngredientType)

    def resolve_all_categories(self, context):
        return Category.objects.all()

    def resolve_all_ingredients(self, context):
        # We can easily optimize query count in the resolve method
        return Ingredient.objects.select_related("category").all()

    def resolve_category(self, context, id=None, name=None):
        if id is not None:
            return Category.objects.get(pk=id)

        if name is not None:
            return Category.objects.get(name=name)

        return None

    def resolve_ingredient(self, context, id=None, name=None):
        if id is not None:
            return Ingredient.objects.get(pk=id)

        if name is not None:
            return Ingredient.objects.get(name=name)

        return None
