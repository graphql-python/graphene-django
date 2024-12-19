import os
import sys

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_PATH + "/examples/")

SECRET_KEY = 1

INSTALLED_APPS = [
    "graphene_django",
    "graphene_django.rest_framework",
    "graphene_django.tests",
    "examples.starwars",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "django_test.sqlite"}
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
    }
]

GRAPHENE = {"SCHEMA": "graphene_django.tests.schema_view.schema"}

ROOT_URLCONF = "graphene_django.tests.urls"
