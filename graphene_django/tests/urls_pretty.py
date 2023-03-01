from django.urls import re_path

from ..views import GraphQLView
from .schema_view import schema

urlpatterns = [re_path(r"^graphql", GraphQLView.as_view(schema=schema, pretty=True))]
