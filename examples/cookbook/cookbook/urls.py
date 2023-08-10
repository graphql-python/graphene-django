from django.contrib import admin
from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import AsyncGraphQLView

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^graphql$", csrf_exempt(AsyncGraphQLView.as_view(graphiql=True))),
]
