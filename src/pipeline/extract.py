from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd
import requests

from src.pipeline.generate_crm import RAW, SEED, TICKERS

BOC_BASE = "https://www.bankofcanada.ca/valet"
FX_SERIES = "FXUSDCAD"

log = logging.getLogger(__name__)

def fetch_json(url: str, attempts: int = 4, backoff: float = 1.5) -> dict:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = backoff ** attempt
            log.warning(
                "fetch failed (attempt %d/%d): %s — retrying in %.1fs",
                attempt, attempts, exc, delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"failed to fetch {url} after {attempts} attempts") from last_error

def extract_fx(days: int = 400) -> pd.DataFrame:
    url = f"{BOC_BASE}/observations/{FX_SERIES}/json?recent={days}"
    log.info("fethcing %s from Bank of Canada", FX_SERIES)
    payload = fetch_json(url)
    
    rows = [
        {"rate_date": obs["d"], "usd_cad": float(obs[FX_SERIES]["v"])}
        for obs in payload["observations"]
        if obs.get(FX_SERIES, {}).get("v") not in (None, "")
    ]
    df = pd.DataFrame(rows).sort_values("rate_date").reset_index(drop=True)
    log.info(
        "got %d observations (%s to %s)",
        len(df), df["rate_date"].min(), df["rate_date"].max(),
    )
    return df

def extract_prices(dates: list[str]) -> pd.DataFrame:
    rng = np.random.default_rng(SEED + 1)
    rows = []
    for ticker, currency in TICKERS.items():
        price = float(rng.uniform(40, 400))
        for date in dates:
            price *= float(np.exp(rng.normal(0, 0.012)))
            rows.append({
                "price_date": date,
                "ticker": ticker,
                "close_price": round(price, 2),
                "currency": currency,
            })
    return pd.DataFrame(rows)

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    RAW.mkdir(parents=True, exist_ok=True)
    fx_path = RAW / "fx_usdcad.csv"

    try:
        fx = extract_fx()
    except RuntimeError as exc:
        if not fx_path.exists():
            raise
        log.warning("extraction failed (%s) — reusing cached snapshot", exc)
        fx = pd.read_csv(fx_path)

    fx.to_csv(fx_path, index=False)
    prices = extract_prices(fx["rate_date"].tolist())
    prices.to_csv(RAW / "prices.csv", index=False)
    log.info("wrote %d fx rows, %d price rows", len(fx), len(prices))


if __name__ == "__main__":
    main()