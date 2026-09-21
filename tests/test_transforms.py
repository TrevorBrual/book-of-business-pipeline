from __future__ import annotations

from pathlib import Path

import pytest

SQL = Path("sql")


@pytest.fixture
def seeded(con):
    con.execute("""
        CREATE TABLE raw.clients AS SELECT * FROM (VALUES
            ('C001', 'Ann',  '  BORG  ', 'ann@x.com',  'V8P 1A1', 'BC', '1980-01-01', 'A001'),
            ('C001', 'ANN',  'Borg',     NULL,          'V8P 1A1', 'BC', '1980-01-01', 'A001'),
            ('C002', 'Bo',   'Chen',     'bo@x.com',    '98101',   'BC', '1975-06-15', 'A001'),
            ('C003', 'Cy',   'Diaz',     'cy@x.com',    NULL,      'ON', '2031-04-02', 'A001')
        ) AS t(client_id, first_name, last_name, email, postal_code, province, date_of_birth, advisor_id)
    """)
    con.execute(SQL.joinpath("staging/stg_clients.sql").read_text())
    return con


def test_trims_whitespace(seeded):
    names = seeded.execute("SELECT last_name FROM staging.stg_clients").df()["last_name"]
    assert (names == names.str.strip()).all()


def test_empty_email_becomes_null(seeded):
    n = seeded.execute(
        "SELECT count(*) FROM staging.stg_clients WHERE email = ''"
    ).fetchone()[0]
    assert n == 0


def test_invalid_postal_codes_flagged(seeded):
    rows = seeded.execute("""
        SELECT client_id FROM staging.stg_clients WHERE NOT postal_code_valid
    """).df()["client_id"].tolist()
    assert set(rows) == {"C002", "C003"}


def test_null_postal_code_is_invalid_not_unknown(seeded):
    result = seeded.execute("""
        SELECT postal_code_valid FROM staging.stg_clients WHERE client_id = 'C003'
    """).fetchone()[0]
    assert result is False


def test_dedupe_prefers_row_with_email(seeded):
    winner = seeded.execute("""
        SELECT email FROM staging.stg_clients WHERE client_id = 'C001' AND dedupe_rank = 1
    """).fetchone()[0]
    assert winner == "ann@x.com"