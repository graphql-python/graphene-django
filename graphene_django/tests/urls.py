from django.urls import path

from ..views import GraphQLView

urlpatterns = [
    path("graphql/batch", GraphQLView.as_view(batch=True)),
    path("graphql", GraphQLView.as_view(graphiql=True)),
]
