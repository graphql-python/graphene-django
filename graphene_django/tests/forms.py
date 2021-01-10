from django import forms
from django.core.exceptions import ValidationError

from .models import Pet


class PetForm(forms.ModelForm):
    class Meta:
        model = Pet
        fields = "__all__"

    def clean_age(self):
        age = self.cleaned_data["age"]
        if age >= 99:
            raise ValidationError("Too old")
        return age
