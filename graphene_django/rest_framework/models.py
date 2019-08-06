from django.db import models


class MyFakeModel(models.Model):
    cool_name = models.CharField(max_length=50)
    created = models.DateTimeField(auto_now_add=True)


class MyFakeModelWithPassword(models.Model):
    cool_name = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
