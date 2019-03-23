from graphene.relay import Connection
from graphene.types.scalars import Int

class CountableConnectionInitial(Connection):
    class Meta:
        abstract = True

    total_count = Int()

    def resolve_total_count(self, info, **kwargs):
        return len(self.iterable)
