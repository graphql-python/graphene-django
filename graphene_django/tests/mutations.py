from graphene import Field

from graphene_django.forms.mutation import DjangoFormMutation, DjangoModelFormMutation

from .forms import PetForm
from .types import PetType


class PetFormMutation(DjangoFormMutation):
    class Meta:
        form_class = PetForm


class PetMutation(DjangoModelFormMutation):
    pet = Field(PetType)

    class Meta:
        form_class = PetForm
