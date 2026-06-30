"""Backwards-compatibility shim for the misspelled ``formating`` module.

The canonical module is now :mod:`graphene_django.debug.exception.formatting`.
This shim re-exports its public symbols so that any third-party code still
importing the legacy name continues to work. It is deprecated and will be
removed in a future major release.
"""

from .formatting import wrap_exception  # noqa: F401  - re-exported for backwards compatibility

__all__ = ["wrap_exception"]
