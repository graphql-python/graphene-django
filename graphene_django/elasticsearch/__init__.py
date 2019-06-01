import warnings
from ..utils import DJANGO_ELASTICSEARCH_DSL_INSTALLED

if not DJANGO_ELASTICSEARCH_DSL_INSTALLED:
    warnings.warn(
        "Use of elasticsearch integration requires the django_elasticsearch_dsl package "
        "be installed. You can do so using `pip install django_elasticsearch_dsl`",
        ImportWarning,
    )
