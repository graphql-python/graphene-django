from graphene_django.types import DjangoObjectType

from .models import Pet


class PetType(DjangoObjectType):
    class Meta:
        model = Pet
        fields = "__all__"
