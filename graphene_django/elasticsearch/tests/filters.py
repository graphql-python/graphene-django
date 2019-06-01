
from graphene_django.elasticsearch.filter import filters
from graphene_django.elasticsearch.filter.filterset import FilterSetES


class ArticleFilterES(FilterSetES):

    headline = filters.StringFilterES(attr='headline')
