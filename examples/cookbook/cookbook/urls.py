from django.conf.urls import url
from django.conf.urls import include
from django.views.decorators.csrf import csrf_exempt
from django.contrib import admin

from graphene_django.views import GraphQLView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^graphql', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    url(r'^graphiql', include('django_graphiql.urls')),
]
