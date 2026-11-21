from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ..sql.tracking import NormalCursorWrapper


@pytest.mark.parametrize(
    ("statement", "is_select"),
    [("  SELECT 1", True), ("UPDATE reporter SET name = 'Ada'", False)],
)
def test_records_composed_sql_query(statement, is_select):
    sql = pytest.importorskip("psycopg2.sql")
    query = sql.Composed([sql.SQL(statement)])
    cursor = Mock()
    db = Mock(connection=object())
    db.ops.last_executed_query.return_value = statement
    logger = SimpleNamespace(object=SimpleNamespace(sql=[]))
    wrapper = NormalCursorWrapper(cursor, db, logger)

    wrapper.execute(query)

    cursor.execute.assert_called_once_with(query, None)
    (recorded_query,) = logger.object.sql
    assert recorded_query.sql == statement
    assert recorded_query.is_select is is_select
