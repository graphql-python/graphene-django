import graphene
from graphene import ObjectType, Schema


class QueryRoot(ObjectType):

    thrower = graphene.String(required=True)
    request = graphene.String(required=True)
    test = graphene.String(who=graphene.String())

    def resolve_thrower(self, args, context, info):
        raise Exception("Throws!")

    def resolve_request(self, args, context, info):
        request = context
        return request.GET.get('q')

    def resolve_test(self, args, context, info):
        return 'Hello %s' % (args.get('who') or 'World')


class MutationRoot(ObjectType):
    write_test = graphene.Field(QueryRoot)

    def resolve_write_test(self, args, context, info):
        return QueryRoot()


schema = Schema(query=QueryRoot, mutation=MutationRoot)
