CREATE OR REPLACE TABLE staging.stg_holdings AS
WITH typed AS (
    SELECT
        trim(holding_id)                    AS holding_id,
        trim(client_id)                     AS client_id,
        upper(trim(ticker))                 AS ticker,
        try_cast(quantity AS INTEGER)       AS quantity,
        try_cast(book_value AS DOUBLE)      AS book_value,
        upper(trim(currency))               AS currency,
        try_cast(as_of_date AS DATE)        AS as_of_date
    FROM raw.holdings
),
expected AS (
    SELECT *, CASE WHEN ticker LIKE '%.TO' THEN 'CAD' ELSE 'USD' END AS expected_currency
    FROM typed
)
SELECT
    *,
    currency IS DISTINCT FROM expected_currency AS currency_mismatch,
    quantity IS NOT NULL AND quantity < 0       AS negative_quantity
FROM expected;