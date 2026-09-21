from __future__ import annotations

import pandas as pd
import pytest

from src.pipeline.dq import load_checks, run_check, summarize


def test_all_checks_have_required_fields():
    for check in load_checks():
        assert set(check) >= {"name", "severity", "description", "query"}
        assert check["severity"] in {"critical", "warning"}
        assert "failing_key" in check["query"]


def test_check_names_are_unique():
    names = [c["name"] for c in load_checks()]
    assert len(names) == len(set(names))
    
@pytest.fixture
def holdings(con):
    con.execute("""
        CREATE TABLE core.fct_holding AS SELECT * FROM (VALUES
            ('H1', 'C001', 100, false, false, 1000.0),
            ('H2', 'C999', 50,  true,  false, 500.0),
            ('H3', 'C001', -10, false, true,  -100.0)
        ) AS t(holding_id, client_id, quantity, orphan_client, negative_quantity, market_value_cad)
    """)
    return con


def test_orphan_check_catches_orphan(holdings):
    check = {
        "name": "holding_client_fk",
        "severity": "critical",
        "description": "test",
        "query": "SELECT holding_id AS failing_key FROM core.fct_holding WHERE orphan_client",
    }
    result = run_check(holdings, check, "testrun")
    assert result["status"] == "fail"
    assert result["failing_rows"] == 1
    assert "H2" in result["sample_keys"]


def test_check_passes_on_clean_data(holdings):
    check = {
        "name": "always_passes",
        "severity": "critical",
        "description": "test",
        "query": "SELECT holding_id AS failing_key FROM core.fct_holding WHERE false",
    }
    assert run_check(holdings, check, "testrun")["status"] == "pass"


def test_broken_sql_reports_error_not_pass(holdings):
    check = {
        "name": "broken",
        "severity": "critical",
        "description": "test",
        "query": "SELECT failing_key FROM core.table_that_does_not_exist",
    }
    assert run_check(holdings, check, "testrun")["status"] == "error"

def test_critical_failure_drives_exit_code():
    results = pd.DataFrame([
        {"status": "pass", "severity": "critical"},
        {"status": "fail", "severity": "warning"},
    ])
    passed, critical, warning = summarize(results)
    assert (passed, critical, warning) == (1, 0, 1)

    results = pd.DataFrame([{"status": "fail", "severity": "critical"}])
    assert summarize(results)[1] == 1