CREATE OR REPLACE TABLE staging.stg_clients AS
WITH typed AS (
    SELECT
        trim(client_id)                        AS client_id,
        trim(first_name)                       AS first_name,
        trim(last_name)                        AS last_name,
        lower(nullif(trim(email), ''))         AS email,
        upper(trim(postal_code))               AS postal_code,
        trim(province)                         AS province,
        try_cast(date_of_birth AS DATE)        AS date_of_birth,
        trim(advisor_id)                       AS advisor_id
    FROM raw.clients
)
SELECT
    *,
        postal_code IS NOT NULL
        AND regexp_matches(postal_code, '^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$') AS postal_code_valid,
        row_number() OVER (
        PARTITION BY client_id
        ORDER BY
            CASE WHEN email IS NOT NULL THEN 0 ELSE 1 END,
            CASE WHEN postal_code IS NOT NULL
                  AND regexp_matches(postal_code, '^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$')
                 THEN 0 ELSE 1 END,
            first_name
    ) AS dedupe_rank
FROM typed;