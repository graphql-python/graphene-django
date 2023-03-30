from django.urls import re_path
from django.contrib import admin

from graphene_django.views import GraphQLView

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^graphql$", GraphQLView.as_view(graphiql=True)),
]
