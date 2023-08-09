from django.db import models

from ..compat import Choices, MissingType


class MyFakeModel(models.Model):
    cool_name = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)


class MyFakeModelWithPassword(models.Model):
    cool_name = models.CharField(max_length=50)
    password = models.CharField(max_length=50)


class MyFakeModelWithDate(models.Model):
    cool_name = models.CharField(max_length=50)
    last_edited = models.DateField()


if Choices is not MissingType:

    class MyFakeModelWithChoiceField(models.Model):
        class ChoiceType(Choices):
            ASDF = "asdf"
            HI = "hi"

        choice_type = models.CharField(
            max_length=4,
            default=ChoiceType.HI.name,
        )

else:

    class MyFakeModelWithChoiceField:
        ...
