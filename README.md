# book-of-business-pipeline

An ELT pipeline that ingests advisor CRM records and market data into a layered
DuckDB warehouse, then runs declarative data quality checks against the results.
The CRM source is synthetic and seeded with known defects — duplicate client IDs,
orphaned holdings, currency codes that contradict the security's listing exchange,
malformed postal codes — so every check can be verified against a manifest of what
was actually broken. Transformations are layered staging → core → marts in SQL,
check results are written to a queryable `dq_results` table, and the whole thing
runs in Docker with pytest coverage on the transform logic.
