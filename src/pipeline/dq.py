from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from src.pipeline.load import connect

CHECKS_PATH = Path("config/dq_checks.yml")
MAX_SAMPLES = 5

log = logging.getLogger(__name__)

def load_checks(path: Path = CHECKS_PATH) -> list[dict]:
    checks = yaml.safe_load(path.read_text())
    names = [c["name"] for c in checks]
    if len(names) != len(set(names)):
        raise ValueError("duplicate check names in config")
    return checks

def run_check(con: duckdb.DuckDBPyConnection, check: dict, run_id: str) -> dict:
    try:
        failures = con.execute(check["query"]).df()
        error = None
    except duckdb.Error as exc:
        log.error("check %s failed to execute: %s", check["name"], exc)
        return {
            "run_id": run_id,
            "check_name": check["name"],
            "severity": check["severity"],
            "description": check["description"],
            "status": "error",
            "failing_rows": None,
            "sample_keys": str(exc)[:200],
        }

    keys = failures["failing_key"].astype(str).head(MAX_SAMPLES).tolist()
    return {
        "run_id": run_id,
        "check_name": check["name"],
        "severity": check["severity"],
        "description": check["description"],
        "status": "pass" if failures.empty else "fail",
        "failing_rows": len(failures),
        "sample_keys": ", ".join(keys),
    }
    
def run_all(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checks = load_checks()
    results = pd.DataFrame([run_check(con, c, run_id) for c in checks])
    results.insert(1, "run_ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    con.execute("CREATE SCHEMA IF NOT EXISTS dq")
    con.execute("CREATE TABLE IF NOT EXISTS dq.dq_results AS SELECT * FROM results LIMIT 0")
    con.execute("INSERT INTO dq.dq_results SELECT * FROM results")
    return results

def summarize(results: pd.DataFrame) -> tuple[int, int, int]:
    failed = results[results["status"].isin(["fail", "error"])]
    critical = len(failed[failed["severity"] == "critical"])
    warning = len(failed[failed["severity"] == "warning"])
    return len(results) - len(failed), critical, warning


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
    con = connect()
    results = run_all(con)
    con.close()

    for row in results.itertuples():
        if row.status != "pass":
            log.warning("%-28s %-8s %s rows  [%s]", row.check_name, row.severity, row.failing_rows, row.sample_keys)

    passed, critical, warning = summarize(results)
    log.info("%d passed, %d critical failures, %d warnings", passed, critical, warning)
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())