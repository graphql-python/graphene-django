class FieldResolverObservable(object):
    """Observable to attach processor by field and resolve it with the field value"""

    def __init__(self):
        """A new Observable by filterset"""
        super(FieldResolverObservable, self).__init__()
        self._fields = {}

    def attach(self, field, processor):
        """Add processor to fields"""
        self._fields[field] = processor

    def resolve(self, field, value):
        """Execute processor of the specific field with the value"""
        if field in self._fields:
            processor = self._fields[field]
            return processor.build_query(value)
