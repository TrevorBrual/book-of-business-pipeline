from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from src.pipeline.load import connect

SQL_DIR = Path("sql")
LAYERS = ("staging", "core", "marts")

log = logging.getLogger(__name__)


def run_layer(con: duckdb.DuckDBPyConnection, layer: str) -> int:
    paths = sorted((SQL_DIR / layer).glob("*.sql"))
    for path in paths:
        log.info("running %s", path.as_posix())
        con.execute(path.read_text())
    return len(paths)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
    con = connect()
    total = sum(run_layer(con, layer) for layer in LAYERS)
    con.close()
    log.info("executed %d models", total)


if __name__ == "__main__":
    main()