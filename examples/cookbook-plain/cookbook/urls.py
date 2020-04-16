from django.urls import path
from django.contrib import admin

from graphene_django.views import GraphQLView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", GraphQLView.as_view(graphiql=True)),
]
