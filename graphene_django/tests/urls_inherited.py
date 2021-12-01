from django.urls import re_path

from ..views import GraphQLView
from .schema_view import schema


class CustomGraphQLView(GraphQLView):
    schema = schema
    graphiql = True
    pretty = True


urlpatterns = [re_path(r"^graphql/inherited/$", CustomGraphQLView.as_view())]
