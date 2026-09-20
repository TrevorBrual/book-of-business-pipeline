from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw")
SEED = 20260919
AS_OF = "2026-09-19"

FIRST = ["Amara", "Devin", "Priya", "Marcus", "Chen", "Sofia", "Liam", "Nadia"]
LAST = ["Okafor", "Reyes", "Sharma", "Nguyen", "Tremblay", "Baptiste", "Kowalski"]
PROVINCES = ["BC", "AB", "ON", "QC", "NS"]

TICKERS = {
    "RY.TO": "CAD", "ENB.TO": "CAD", "SHOP.TO": "CAD",
    "AAPL": "USD", "MSFT": "USD", "JPM": "USD",
}

def pick(df: pd.DataFrame, k: int, rng) -> pd.Index:
    """Return k random index labels from df, without replacement."""
    return df.index[rng.choice(len(df), size=k, replace=False)]

# Generating clean data
def make_advisors(n: int, rng) -> pd.DataFrame:
    return pd.DataFrame({
        "advisor_id": [f"A{i + 1:03d}" for i in range(n)],
        "advisor_name": [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(n)],
        "branch": rng.choice(["Victoria", "Vancouver", "Calgary", "Toronto"], size=n),
    })

def make_clients(n: int, advisors: pd.DataFrame, rng) -> pd.DataFrame:
    first = rng.choice(FIRST, size=n)
    last = rng.choice(LAST, size=n)
    birth = pd.Timestamp("1955-01-01") + pd.to_timedelta(
        rng.integers(0, 55 * 365, size=n), unit="D"
    )
    
    letters, digits = list("VTKLMHJ"), list("0123456789")
    return pd.DataFrame({
        "client_id":[f"C{i + 1:05d}" for i in range(n)],
        "first_name": first,
        "last_name": last,
        "email": [f"{f}.{l}@example.com".lower() for f, l in zip(first, last)],
        "postal_code": [
            f"{rng.choice(letters)}{rng.choice(digits)}{rng.choice(letters)}"
            f" {rng.choice(digits)}{rng.choice(letters)}{rng.choice(digits)}"
            for _ in range(n)
        ],
        "province": rng.choice(PROVINCES, size=n),
        "date_of_birth": birth.strftime("%Y-%m-%d"),
        "advisor_id": rng.choice(advisors["advisor_id"], size=n),
    })

def make_holdings(clients: pd.DataFrame, rng) -> pd.DataFrame:
    rows = []
    for client_id in clients["client_id"]:
        for _ in range(int(rng.integers(1, 6))):
            ticker = str(rng.choice(list(TICKERS)))
            rows.append({
                "holding_id": None,
                "client_id": client_id,
                "ticker": ticker,
                "quantity": int(rng.integers(5, 500)),
                "book_value": round(float(rng.uniform(500, 90_000)), 2),
                "currency": TICKERS[ticker],
                "as_of_date": AS_OF,
            })
    df = pd.DataFrame(rows)
    df["holding_id"] = [f"H{i + 1:06d}" for i in range(len(df))]
    return df

def inject_defects(clients: pd.DataFrame, holdings: pd.DataFrame, rng):
    # 1) Missing contact info -> a client you cannot reach
    manifest: dict[str, list[str]] = {}
    idx = pick(clients, 18, rng)
    clients.loc[idx, "email"] = None
    manifest["client_email_null"] = clients.loc[idx, "client_id"].tolist()
    
    # 2) Inconsistent formatting -> same person, three different ways of writing their name (Spelling)
    idx = pick(clients, 25, rng)
    clients.loc[idx, "last_name"] = "  " + clients.loc[idx, "last_name"].str.upper() + " "
    manifest["client_name_formatting"] = clients.loc[idx, "client_id"].tolist()
    
    # 3) Non-canadian postal codes
    idx = pick(clients, 14, rng)
    clients.loc[idx, "postal_code"] = rng.choice(["98101", "V8P", "", "N/A"], size=len(idx))
    manifest["client_postal_invalid"] = clients.loc[idx, "client_id"].tolist()
    
    # 4) Birth dates in the future -> a client who is not yet born
    idx = pick(clients, 7, rng)
    clients.loc[idx, "date_of_birth"] = "2031-04-02"
    manifest["client_dob_future"] = clients.loc[idx, "client_id"].tolist()
    
    # 5) Currency that contradicts the security's listing exchange.
    idx = pick(holdings, 22, rng)
    holdings.loc[idx, "currency"] = holdings.loc[idx, "currency"].map(
        {"CAD": "USD", "USD": "CAD"}
    )
    manifest["holding_currency_mismatch"] = holdings.loc[idx, "holding_id"].tolist()

    # 6) Orphans — holdings pointing at clients that don't exist.
    idx = pick(holdings, 15, rng)
    holdings.loc[idx, "client_id"] = "C99999"
    manifest["holding_orphan_client"] = holdings.loc[idx, "holding_id"].tolist()

    # 7) Negative share counts.
    idx = pick(holdings, 9, rng)
    holdings.loc[idx, "quantity"] = -holdings.loc[idx, "quantity"]
    manifest["holding_negative_quantity"] = holdings.loc[idx, "holding_id"].tolist()

    # 8) Duplicate client records, appended last so earlier indices stay valid.
    idx = pick(clients, 12, rng)
    dupes = clients.loc[idx].copy()
    dupes["first_name"] = dupes["first_name"].str.upper()
    manifest["client_duplicate_id"] = dupes["client_id"].tolist()
    clients = pd.concat([clients, dupes], ignore_index=True)

    return clients, holdings, manifest

def main() -> None:
    rng = np.random.default_rng(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    advisors = make_advisors(20, rng)
    clients = make_clients(600, advisors, rng)
    holdings = make_holdings(clients, rng)
    clients, holdings, manifest = inject_defects(clients, holdings, rng)
    
    advisors.to_csv(RAW / "advisors.csv", index=False)
    clients.to_csv(RAW / "clients.csv", index=False)
    holdings.to_csv(RAW / "holdings.csv", index=False)
    (RAW / "defect_manifest.json").write_text(json.dumps(manifest, indent=2))

    total = sum(len(v) for v in manifest.values())
    print(f"advisors={len(advisors)} clients={len(clients)} holdings={len(holdings)}")
    print(f"injected {total} defects across {len(manifest)} categories")


if __name__ == "__main__":
    main()

