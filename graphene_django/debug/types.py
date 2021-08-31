from graphene import List, ObjectType

from .sql.types import DjangoDebugSQL
from .exception.types import DjangoDebugException


class DjangoDebug(ObjectType):
    class Meta:
        description = "Debugging information for the current query."

    sql = List(DjangoDebugSQL, description="Executed SQL queries for this API query.")
    exceptions = List(
        DjangoDebugException, description="Raise exceptions for this API query."
    )
