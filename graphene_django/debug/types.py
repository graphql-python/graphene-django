from graphene import List, ObjectType

from .sql.types import DjangoDebugSQL


class DjangoDebug(ObjectType):
    class Meta:
        description = "Debugging information for the current query."

    sql = List(DjangoDebugSQL, description="Executed SQL queries for this API query.")
