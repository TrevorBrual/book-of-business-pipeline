CREATE OR REPLACE TABLE core.fct_holding AS
SELECT
    h.holding_id,
    h.client_id,
    h.ticker,
    h.quantity,
    h.book_value,
    h.currency,
    h.as_of_date,
    h.currency_mismatch,
    h.negative_quantity,
    p.close_price,
    f.usd_cad,
    f.is_carried_forward                        AS fx_carried_forward,
    c.client_id IS NULL                         AS orphan_client,
    h.quantity * p.close_price                  AS market_value_local,
    CASE
        WHEN h.currency = 'CAD' THEN h.quantity * p.close_price
        WHEN h.currency = 'USD' THEN h.quantity * p.close_price * f.usd_cad
    END                                         AS market_value_cad
FROM staging.stg_holdings h
LEFT JOIN staging.stg_fx f
    ON f.rate_date = h.as_of_date
LEFT JOIN staging.stg_prices p
    ON p.price_date = h.as_of_date AND p.ticker = h.ticker
LEFT JOIN core.dim_client c
    ON c.client_id = h.client_id;