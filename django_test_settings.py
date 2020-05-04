import sys
import os

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_PATH + '/examples/')

SECRET_KEY = 1

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    'graphene_django',
    'graphene_django.rest_framework',
    'graphene_django.tests',
    'starwars',
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django_test.sqlite',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
    },
]

GRAPHENE = {
    'SCHEMA': 'graphene_django.tests.schema_view.schema'
}

ROOT_URLCONF = 'graphene_django.tests.urls'
