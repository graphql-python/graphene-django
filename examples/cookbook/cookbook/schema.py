import cookbook.ingredients.schema
import graphene

from graphene_django.debug import DjangoDebug

# print cookbook.ingredients.schema.Query._meta.graphql_type.get_fields()['allIngredients'].args


class Query(cookbook.ingredients.schema.Query, graphene.ObjectType):
    debug = graphene.Field(DjangoDebug, name='__debug')


schema = graphene.Schema(query=Query)
