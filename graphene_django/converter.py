from django.utils.encoding import force_text
from neomodel import (
    AliasProperty,
    ArrayProperty,
    BooleanProperty,
    DateProperty,
    DateTimeProperty,
    EmailProperty,
    FloatProperty,
    IntegerProperty,
    JSONProperty,
    RegexProperty,
    StringProperty,
    UniqueIdProperty,
    ZeroOrMore,
    ZeroOrOne,
    One,
    OneOrMore,
)

from neomodel.relationship_manager import RelationshipDefinition

try:
    # TimurMardanov fork branch. Supports contain 2D-xD arrays
    from neomodel import JsonArrayProperty  # noqa
    jsonArrayProperty = JsonArrayProperty
except BaseException:
    jsonArrayProperty = JSONProperty

from graphene import (
    ID,
    Boolean,
    Dynamic,
    Enum,
    Field,
    Float,
    Int,
    List,
    NonNull,
    String,
    UUID,
    DateTime,
    Date,
    Time,
)
from graphene.types.json import JSONString
from graphene.utils.str_converters import to_camel_case, to_const
from graphql import assert_valid_name

from .compat import ArrayField, HStoreField, JSONField, RangeField
from .fields import DjangoListField, DjangoConnectionField
from .utils import import_single_dispatch

singledispatch = import_single_dispatch()


REQUIRED_CARDINALITY = (One, OneOrMore, )
NOT_REQUIRED_CARDINALITY = (ZeroOrMore, ZeroOrOne,)


@singledispatch
def define_null_parameter(manager):
    raise Exception(
        "Don't know how to convert the Neomodel relationship field"
    )


@define_null_parameter.register(REQUIRED_CARDINALITY[0])
@define_null_parameter.register(REQUIRED_CARDINALITY[1])
def return_required(field):
    return True


@define_null_parameter.register(NOT_REQUIRED_CARDINALITY[0])
@define_null_parameter.register(NOT_REQUIRED_CARDINALITY[1])
def return_required(field):
    return False


def convert_choice_name(name):
    name = to_const(force_text(name))
    try:
        assert_valid_name(name)
    except AssertionError:
        name = "A_%s" % name
    return name


def get_choices(choices):
    converted_names = []
    for value, help_text in choices.items():
        if isinstance(help_text, (tuple, list)):
            for choice in get_choices(help_text):
                yield choice
        else:
            name = convert_choice_name(value)
            while name in converted_names:
                name += "_" + str(len(converted_names))
            converted_names.append(name)
            description = help_text
            yield name, value, description


def convert_django_field_with_choices(field, registry=None):
    if registry is not None:
        converted = registry.get_converted_field(field)
        if converted:
            return converted
    choices = getattr(field, "choices", None)
    if choices:
        field_class = field.owner
        name = to_camel_case("{}_{}".format(field_class.__name__, field.name))
        choices = list(get_choices(dict(choices)))
        named_choices = [(c[0], c[1]) for c in choices]
        named_choices_descriptions = {c[0]: c[2] for c in choices}

        class EnumWithDescriptionsType(object):
            @property
            def description(self):
                return named_choices_descriptions[self.name]

        enum = Enum(name, list(named_choices), type=EnumWithDescriptionsType)
        converted = enum(description=field.help_text, required=field.required)
    else:
        converted = convert_django_field(field, registry)
    if registry is not None:
        registry.register_converted_field(field, converted)
    return converted


@singledispatch
def convert_django_field(field, registry=None):
    raise Exception(
        "Don't know how to convert the Django field %s (%s)" % (field, field.__class__)
    )


@convert_django_field.register(StringProperty)
@convert_django_field.register(RegexProperty)
def convert_field_to_string(field, registry=None):
    return String(description=field.help_text)


@convert_django_field.register(IntegerProperty)
def convert_field_to_int(field, registry=None):
    return Int(description=field.help_text)


@convert_django_field.register(BooleanProperty)
def convert_field_to_boolean(field, registry=None):
    return NonNull(Boolean, description=field.help_text)


@convert_django_field.register(FloatProperty)
def convert_field_to_float(field, registry=None):
    return Float(description=field.help_text)


@convert_django_field.register(DateTimeProperty)
def convert_datetime_to_string(field, registry=None):
    return DateTime(description=field.help_text)


@convert_django_field.register(DateProperty)
def convert_date_to_string(field, registry=None):
    return Date(description=field.help_text)


@convert_django_field.register(RelationshipDefinition)
def convert_onetoone_field_to_djangomodel(field, registry=None):
    model = field._raw_class
    manager = field.build_manager(model, 'field')

    def dynamic_type():
        _type = registry.get_type_for_model(manager.definition['node_class'])
        if not _type:
            return

        if _type._meta.connection:
            # Use a DjangoFilterConnectionField if there are
            # defined filter_fields in the DjangoObjectType Meta
            if _type._meta.neomodel_filter_fields:
                from .filter.fields import DjangoFilterConnectionField  # noqa
                return DjangoFilterConnectionField(_type)
            return DjangoConnectionField(_type)
        return DjangoListField(_type)

    return Dynamic(dynamic_type)


@convert_django_field.register(ArrayProperty)
def convert_array_to_list(field, registry=None):
    base_property = field.base_property or StringProperty()
    return List(description=field.help_text,
                of_type=convert_django_field(base_property).__class__)


@convert_django_field.register(JSONProperty)
@convert_django_field.register(jsonArrayProperty)
def convert_json_field_to_string(field, registry=None):
    return JSONString(description=field.help_text)
