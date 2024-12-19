from django import forms
from pytest import raises

import graphene
from graphene_django import DjangoObjectType

from ...tests.models import CHOICES, Film, Reporter
from ..types import DjangoFormInputObjectType

# Reporter a_choice CHOICES = ((1, "this"), (2, _("that")))
THIS = CHOICES[0][0]
THIS_ON_CLIENT_CONVERTED = "A_1"

# Film genre choices=[("do", "Documentary"), ("ac", "Action"), ("ot", "Other")],
DOCUMENTARY = "do"
DOCUMENTARY_ON_CLIENT_CONVERTED = "DO"


class FilmForm(forms.ModelForm):
    class Meta:
        model = Film
        exclude = ()


class ReporterType(DjangoObjectType):
    class Meta:
        model = Reporter
        fields = "__all__"


class ReporterForm(forms.ModelForm):
    class Meta:
        model = Reporter
        exclude = ("pets", "email", "fans")


class MyForm(forms.Form):
    text_field = forms.CharField()
    int_field = forms.IntegerField()


def test_needs_form_class():
    with raises(Exception) as exc:

        class MyInputType(DjangoFormInputObjectType):
            pass

    assert exc.value.args[0] == "form_class is required for DjangoFormInputObjectType"


def test_type_from_modelform_has_input_fields():
    class ReporterInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = ReporterForm
            only_fields = ("first_name", "last_name", "a_choice")

    fields = ["first_name", "last_name", "a_choice", "id"]
    assert all(f in ReporterInputType._meta.fields for f in fields)


def test_type_from_form_has_input_fields():
    class MyFormInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = MyForm

    fields = ["text_field", "int_field", "id"]
    assert all(f in MyFormInputType._meta.fields for f in fields)


def test_type_custom_id_field():
    class MyFormInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = MyForm
            add_id_field_name = "pk"

    fields = ["text_field", "int_field", "pk"]
    assert all(f in MyFormInputType._meta.fields for f in fields)
    assert MyFormInputType._meta.fields["pk"].type is graphene.ID


def test_type_custom_id_field_type():
    class MyFormInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = MyForm
            add_id_field_name = "pk"
            add_id_field_type = graphene.String(required=False)

    fields = ["text_field", "int_field", "pk"]
    assert all(f in MyFormInputType._meta.fields for f in fields)
    assert MyFormInputType._meta.fields["pk"].type is graphene.String


class MockQuery(graphene.ObjectType):
    a = graphene.String()


def test_mutation_with_form_djangoforminputtype():
    class MyFormInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = MyForm

    class MyFormMutation(graphene.Mutation):
        class Arguments:
            form_data = MyFormInputType(required=True)

        result = graphene.Boolean()

        def mutate(_root, _info, form_data):
            form = MyForm(data=form_data)
            if form.is_valid():
                result = form.cleaned_data == {
                    "text_field": "text",
                    "int_field": 777,
                }
                return MyFormMutation(result=result)
            return MyFormMutation(result=False)

    class Mutation(graphene.ObjectType):
        myForm_mutation = MyFormMutation.Field()

    schema = graphene.Schema(query=MockQuery, mutation=Mutation)

    result = schema.execute(
        """ mutation MyFormMutation($formData: MyFormInputType!) {
            myFormMutation(formData: $formData) {
                result
            }
        }
        """,
        variable_values={"formData": {"textField": "text", "intField": 777}},
    )
    assert result.errors is None
    assert result.data == {"myFormMutation": {"result": True}}


def test_mutation_with_modelform_djangoforminputtype():
    class ReporterInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = ReporterForm
            object_type = ReporterType
            only_fields = ("first_name", "last_name", "a_choice")

    class ReporterMutation(graphene.Mutation):
        class Arguments:
            reporter_data = ReporterInputType(required=True)

        result = graphene.Field(ReporterType)

        def mutate(_root, _info, reporter_data):
            reporter = Reporter.objects.get(pk=reporter_data.id)
            form = ReporterForm(data=reporter_data, instance=reporter)
            if form.is_valid():
                reporter = form.save()
                return ReporterMutation(result=reporter)

            return ReporterMutation(result=None)

    class Mutation(graphene.ObjectType):
        report_mutation = ReporterMutation.Field()

    schema = graphene.Schema(query=MockQuery, mutation=Mutation)

    reporter = Reporter.objects.create(
        first_name="Bob", last_name="Roberts", a_choice=THIS
    )

    result = schema.execute(
        """ mutation ReportMutation($reporterData: ReporterInputType!) {
            reportMutation(reporterData: $reporterData) {
                result {
                    id,
                    firstName,
                    lastName,
                    aChoice
                }
            }
        }
        """,
        variable_values={
            "reporterData": {
                "id": reporter.pk,
                "firstName": "Dave",
                "lastName": "Smith",
                "aChoice": THIS_ON_CLIENT_CONVERTED,
            }
        },
    )
    assert result.errors is None
    assert result.data["reportMutation"]["result"] == {
        "id": "1",
        "firstName": "Dave",
        "lastName": "Smith",
        "aChoice": THIS_ON_CLIENT_CONVERTED,
    }
    assert Reporter.objects.count() == 1
    reporter.refresh_from_db()
    assert reporter.first_name == "Dave"


def reporter_enum_convert_mutation_result(
    ReporterInputType, choice_val_on_client=THIS_ON_CLIENT_CONVERTED
):
    class ReporterMutation(graphene.Mutation):
        class Arguments:
            reporter = ReporterInputType(required=True)

        result_str = graphene.String()
        result_int = graphene.Int()

        def mutate(_root, _info, reporter):
            if isinstance(reporter.a_choice, int) or reporter.a_choice.isdigit():
                return ReporterMutation(result_int=reporter.a_choice, result_str=None)
            return ReporterMutation(result_int=None, result_str=reporter.a_choice)

    class Mutation(graphene.ObjectType):
        report_mutation = ReporterMutation.Field()

    schema = graphene.Schema(query=MockQuery, mutation=Mutation)

    return schema.execute(
        """ mutation ReportMutation($reporter: ReporterInputType!) {
            reportMutation(reporter: $reporter) {
                resultStr,
                resultInt
            }
        }
        """,
        variable_values={"reporter": {"aChoice": choice_val_on_client}},
    )


def test_enum_not_converted():
    class ReporterInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = ReporterForm
            only_fields = ("a_choice",)

    result = reporter_enum_convert_mutation_result(ReporterInputType)
    assert result.errors is None
    assert result.data["reportMutation"]["resultStr"] == THIS_ON_CLIENT_CONVERTED
    assert result.data["reportMutation"]["resultInt"] is None
    assert ReporterInputType._meta.fields["a_choice"].type is graphene.String


def test_enum_is_converted_to_original():
    class ReporterInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = ReporterForm
            object_type = ReporterType
            only_fields = ("a_choice",)

    result = reporter_enum_convert_mutation_result(ReporterInputType)
    assert result.errors is None
    assert result.data["reportMutation"]["resultInt"] == THIS
    assert result.data["reportMutation"]["resultStr"] is None
    assert (
        ReporterInputType._meta.fields["a_choice"].type.__name__
        == "AChoiceEnumBackConvString"
    )


def test_convert_choices_to_enum_is_false_and_field_type_as_in_model():
    class ReporterTypeNotConvertChoices(DjangoObjectType):
        class Meta:
            model = Reporter
            convert_choices_to_enum = False
            fields = "__all__"

    class ReporterInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = ReporterForm
            object_type = ReporterTypeNotConvertChoices
            only_fields = ("a_choice",)

    result = reporter_enum_convert_mutation_result(ReporterInputType, THIS)
    assert result.errors is None
    assert result.data["reportMutation"]["resultInt"] == THIS
    assert result.data["reportMutation"]["resultStr"] is None
    assert ReporterInputType._meta.fields["a_choice"].type is graphene.Int


def enum_convert_mutation_result_film(FilmInputType):
    class FilmMutation(graphene.Mutation):
        class Arguments:
            film = FilmInputType(required=True)

        result = graphene.String()

        def mutate(_root, _info, film):
            return FilmMutation(result=film.genre)

    class Mutation(graphene.ObjectType):
        film_mutation = FilmMutation.Field()

    schema = graphene.Schema(query=MockQuery, mutation=Mutation)

    return schema.execute(
        """ mutation FilmMutation($film: FilmInputType!) {
            filmMutation(film: $film) {
                result
            }
        }
        """,
        variable_values={"film": {"genre": DOCUMENTARY_ON_CLIENT_CONVERTED}},
    )


def test_enum_not_converted_required_non_number():
    class FilmInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = FilmForm
            only_fields = ("genre",)

    result = enum_convert_mutation_result_film(FilmInputType)
    assert result.errors is None
    assert result.data["filmMutation"]["result"] == DOCUMENTARY_ON_CLIENT_CONVERTED


def test_enum_is_converted_to_original_required_non_number():
    class FilmType(DjangoObjectType):
        class Meta:
            model = Film
            fields = "__all__"

    class FilmInputType(DjangoFormInputObjectType):
        class Meta:
            form_class = FilmForm
            object_type = FilmType
            only_fields = ("genre",)

    result = enum_convert_mutation_result_film(FilmInputType)
    assert result.errors is None
    assert result.data["filmMutation"]["result"] == DOCUMENTARY
