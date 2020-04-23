from django.db import models

from ..ingredients.models import Ingredient


class Recipe(models.Model):
    title = models.CharField(max_length=100)
    instructions = models.TextField()

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="amounts", on_delete=models.CASCADE)
    ingredient = models.ForeignKey(
        Ingredient, related_name="used_by", on_delete=models.CASCADE
    )
    amount = models.FloatField()
    unit = models.CharField(
        max_length=20,
        choices=(
            ("unit", "Units"),
            ("kg", "Kilograms"),
            ("l", "Litres"),
            ("st", "Shots"),
        ),
    )
