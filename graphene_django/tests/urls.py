from django.urls import re_path

from ..views import GraphQLView

urlpatterns = [
    re_path(r"^graphql/batch", GraphQLView.as_view(batch=True)),
    re_path(r"^graphql", GraphQLView.as_view(graphiql=True)),
]
