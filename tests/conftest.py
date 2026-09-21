from __future__ import annotations

from collections.abc import Iterator

import duckdb
import pytest


@pytest.fixture
def con() -> Iterator[duckdb.DuckDBPyConnection]:
    connection = duckdb.connect(":memory:")
    for schema in ("raw", "staging", "core", "dq"):
        connection.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    yield connection
    connection.close()