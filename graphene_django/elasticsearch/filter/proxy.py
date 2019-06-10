class QuerysetProxy(object):
    """Bridge to Queryset through ES query"""

    def __init__(self, search):
        """Taking as search, the ES search resolved by DjangoESFilterConnectionField"""
        self.search = search

    def apply_query(self, method, *args, **kwargs):
        """Helper method to apply mutation to ES Query"""
        if hasattr(self.search, method):
            self.search = getattr(self.search, method)(*args, **kwargs)

    def __len__(self):
        """Bridget method to response the ES count as QS len"""
        return self.search.count()

    def __getitem__(self, k):
        """Applying slice to ES and generating a QS from that"""
        _slice = self.search.__getitem__(k)
        return _slice.to_queryset()


class ManagerProxy(object):
    """Bridge to Queryset through ES query"""

    def __init__(self, search_manager):
        """Taking as search, the ES search resolved by DjangoESFilterConnectionField"""
        self.search_manager = search_manager

    def get_queryset(self):
        """Returning self as Queryset to be the bridge"""
        return QuerysetProxy(search=self.search_manager())
