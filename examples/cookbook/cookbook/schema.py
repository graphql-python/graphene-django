import cookbook.ingredients.schema
import graphene


# print cookbook.ingredients.schema.Query._meta.graphql_type.get_fields()['allIngredients'].args


class Query(cookbook.ingredients.schema.Query, graphene.ObjectType):
    pass

schema = graphene.Schema(query=Query)
