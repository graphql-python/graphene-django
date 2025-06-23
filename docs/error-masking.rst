Custom GraphQL Error Masking
============================

This project includes a custom error formatting function for GraphQL
responses that masks sensitive error details from clients.

Purpose
-------

- Prevent exposing internal error details for security and user experience.
- Allow whitelisting of exception classes that should be exposed as-is.
- Return a generic error message for all other exceptions.

Configuration
-------------

You can control the behavior using the ``GRAPHENE_ERRORS`` setting in your
Django settings file under the ``GRAPHENE`` namespace:

.. code-block:: python

    GRAPHENE = {
        "GRAPHENE_ERRORS": {
            "MASK_EXCEPTIONS": True,  # Enable or disable masking
            "ERROR_MESSAGE": "A custom error message.",  # Defaults to "Something went wrong. Please try again later."
            "WHITELISTED_EXCEPTIONS": [
                "ValidationError",  # Whitelist by class name
                "django.core.exceptions.ValidationError", # Whitelist by full module path
                "myapp.custom_exceptions.MyCustomException", # Custom exception whitelist by full path
            ],
        }
    }

Behavior
--------

- If ``MASK_EXCEPTIONS`` is False, all errors are returned fully formatted.
- If True, errors not in the whitelist will return only the generic message.
- Whitelisted exceptions are returned with full error details.

Usage
-----

The masking is automatically applied to the error responses of GraphQL
queries and mutations through a custom error formatter method.

You can modify or extend the whitelisted exceptions as needed to suit your
project's error handling policy.

