from django import forms
from cookbook.ingredients.models import Category, Ingredient


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        exclude = []


class IngredientForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        exclude = []
    
