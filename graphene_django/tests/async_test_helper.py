from asgiref.sync import async_to_sync


def assert_async_result_equal(schema, query, result):
    async_result = async_to_sync(schema.execute_async)(query)
    assert async_result == result
