from cookbook.ingredients.models import Category, Ingredient
from django.contrib import admin


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category")
    list_editable = ("name", "category")


admin.site.register(Category)
