CREATE OR REPLACE TABLE staging.stg_prices AS
SELECT
    try_cast(price_date AS DATE)    AS price_date,
    upper(trim(ticker))             AS ticker,
    try_cast(close_price AS DOUBLE) AS close_price,
    upper(trim(currency))           AS currency
FROM raw.prices;