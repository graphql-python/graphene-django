import binascii

from django.core.exceptions import ValidationError
from django import forms
from django.forms import CharField, Field, MultipleChoiceField
from django.utils.translation import gettext_lazy as _

from graphql_relay import from_global_id


class GlobalIDFormField(Field):
    default_error_messages = {"invalid": _("Invalid ID specified.")}

    def clean(self, value):
        if not value and not self.required:
            return None

        try:
            _type, _id = from_global_id(value)
        except (TypeError, ValueError, UnicodeDecodeError, binascii.Error):
            raise ValidationError(self.error_messages["invalid"])

        try:
            CharField().clean(_id)
            CharField().clean(_type)
        except ValidationError:
            raise ValidationError(self.error_messages["invalid"])

        return value


class GlobalIDMultipleChoiceField(MultipleChoiceField):
    default_error_messages = {
        "invalid_choice": _("One of the specified IDs was invalid (%(value)s)."),
        "invalid_list": _("Enter a list of values."),
    }

    def valid_value(self, value):
        # Clean will raise a validation error if there is a problem
        GlobalIDFormField().clean(value)
        return True


class HeaderForm(forms.Form):
    # make a ChoiceField for 'JWT' and other methods -- use a widget?
    headers = forms.CharField(
        help_text="Enter auth method to be stored in the <head> as HTTP_AUTHORIZATION",
        initial="JWT ",
    )

    def clean_auth(self):
        data = self.cleaned_data["headers"]

        # raise ValidationError()

        # Remember to always return the cleaned data.
        return data
