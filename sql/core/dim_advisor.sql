CREATE OR REPLACE TABLE core.dim_advisor AS
SELECT trim(advisor_id) AS advisor_id, trim(advisor_name) AS advisor_name, trim(branch) AS branch
FROM raw.advisors;