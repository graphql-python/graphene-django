from django.conf.urls import url
from graphql_django_view import GraphQLView

from .schema_view import schema

urlpatterns = [
    url(r'^graphql', GraphQLView.as_view(schema=schema, pretty=True)),
]
