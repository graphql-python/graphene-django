from django.conf.urls import include, url
from django.contrib import admin

from cookbook.schema import schema
from graphene_django.views import GraphQLView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^graphql', GraphQLView.as_view(graphiql=True)),
]
