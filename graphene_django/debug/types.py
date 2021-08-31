from graphene import List, ObjectType, Int

from .sql.types import DjangoDebugSQL
from .exception.types import DjangoDebugException


class DjangoDebug(ObjectType):
    class Meta:
        description = "Debugging information for the current query."

    sql = List(DjangoDebugSQL, description="Executed SQL queries for this API query.")
    sql_count = Int(description="number of executed SQL queries for this API query.")
    exceptions = List(
        DjangoDebugException, description="Raise exceptions for this API query."
    )

    def resolve_sql_count(root, info):
        return len(root.sql)
