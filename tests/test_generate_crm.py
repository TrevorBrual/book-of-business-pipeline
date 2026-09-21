from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.pipeline.generate_crm import (
    SEED,
    TICKERS,
    inject_defects,
    make_advisors,
    make_clients,
    make_holdings,
    pick,
)


@pytest.fixture
def clean_data():
    rng = np.random.default_rng(SEED)
    advisors = make_advisors(5, rng)
    clients = make_clients(50, advisors, rng)
    holdings = make_holdings(clients, rng)
    return advisors, clients, holdings


def test_clean_clients_have_no_defects(clean_data):
    _, clients, _ = clean_data
    assert clients["client_id"].is_unique
    assert clients["email"].notna().all()
    assert (clients["last_name"] == clients["last_name"].str.strip()).all()


def test_clean_holdings_reference_real_clients(clean_data):
    _, clients, holdings = clean_data
    assert holdings["client_id"].isin(clients["client_id"]).all()
    assert (holdings["quantity"] > 0).all()


def test_clean_holdings_have_correct_currency(clean_data):
    _, _, holdings = clean_data
    expected = holdings["ticker"].map(TICKERS)
    assert (holdings["currency"] == expected).all()


def test_generation_is_deterministic():
    def build():
        rng = np.random.default_rng(SEED)
        advisors = make_advisors(5, rng)
        clients = make_clients(50, advisors, rng)
        return clients

    pd.testing.assert_frame_equal(build(), build())


def test_pick_returns_distinct_labels(clean_data):
    _, clients, _ = clean_data
    rng = np.random.default_rng(1)
    idx = pick(clients, 10, rng)
    assert len(idx) == 10
    assert len(set(idx)) == 10
    
def test_manifest_matches_injected_defects():
    rng = np.random.default_rng(SEED)
    advisors = make_advisors(5, rng)
    clients = make_clients(50, advisors, rng)
    holdings = make_holdings(clients, rng)
    clients, holdings, manifest = inject_defects(clients, holdings, rng)

    assert set(clients.loc[clients["email"].isna(), "client_id"]) >= set(
        manifest["client_email_null"]
    )
    assert set(holdings.loc[holdings["quantity"] < 0, "holding_id"]) == set(
        manifest["holding_negative_quantity"]
    )
    assert holdings.loc[
        holdings["holding_id"].isin(manifest["holding_orphan_client"]), "client_id"
    ].eq("C99999").all()

    clients = make_clients(200, advisors, rng)