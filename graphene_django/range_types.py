from graphene import ObjectType
from graphene import (
    Float,
    Int,
    DateTime,
    Date
)

class RangeResolver:
    def resolve_lower(parent, info):
        return parent.lower
    def resolve_upper(parent, info):
        return parent.upper

class DateTimeRangeType(RangeResolver, ObjectType):
    lower = DateTime()
    upper = DateTime()

class DateRangeType(RangeResolver, ObjectType):
    lower = Date()
    upper = Date()

class IntRangeType(RangeResolver, ObjectType):
    lower = Int()
    upper = Int()

class FloatRangeType(RangeResolver, ObjectType):
    lower = Float()
    upper = Float()
