CREATE OR REPLACE TABLE core.dim_client AS
SELECT
    client_id, first_name, last_name, email, postal_code,
    postal_code_valid, province, date_of_birth, advisor_id
FROM staging.stg_clients
WHERE dedupe_rank = 1;