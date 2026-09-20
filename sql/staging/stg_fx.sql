CREATE OR REPLACE TABLE staging.stg_fx AS
WITH typed AS (
    SELECT try_cast(rate_date AS DATE) AS rate_date, try_cast(usd_cad AS DOUBLE) AS usd_cad
    FROM raw.fx_usdcad
    WHERE try_cast(usd_cad AS DOUBLE) IS NOT NULL
),
calendar AS (
    SELECT unnest(generate_series(
        (SELECT min(rate_date) FROM typed),
        (SELECT max(rate_date) FROM typed) + INTERVAL 7 DAY,
        INTERVAL 1 DAY
    ))::DATE AS rate_date
)
SELECT
    c.rate_date,
    last_value(t.usd_cad IGNORE NULLS) OVER (ORDER BY c.rate_date) AS usd_cad,
    t.usd_cad IS NULL AS is_carried_forward
FROM calendar c
LEFT JOIN typed t USING (rate_date);