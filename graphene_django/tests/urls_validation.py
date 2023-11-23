from django.urls import path

from graphene.validation import DisableIntrospection

from ..views import GraphQLView
from .schema_view import schema


class View(GraphQLView):
    schema = schema


urlpatterns = [
    path("graphql/", View.as_view()),
    path("graphql/validation/", View.as_view(validation_rules=(DisableIntrospection,))),
]
