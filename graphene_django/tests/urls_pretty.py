from django.urls import path

from ..views import GraphQLView
from .schema_view import schema

urlpatterns = [path("graphql", GraphQLView.as_view(schema=schema, pretty=True))]
