from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from src.pipeline.generate_crm import RAW

DB_PATH = Path("data/warehouse.duckdb")
SCHEMAS = ("raw", "staging", "core", "marts")

log = logging.getLogger(__name__)

def connect() -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    for schema in SCHEMAS:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    return con

def load_raw(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts = {}
    for csv_path in sorted(RAW.glob("*.csv")):
        table = csv_path.stem
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}', all_varchar = true)
        """)
        counts[table] = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        log.info("loaded raw.%s (%d rows)", table, counts[table])
    return counts

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
    con = connect()
    counts = load_raw(con)
    con.close()
    log.info("loaded %d tables, %d total rows", len(counts), sum(counts.values()))


if __name__ == "__main__":
    main()  