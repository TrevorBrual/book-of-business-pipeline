# book-of-business-pipeline

![ci](https://github.com/TrevorBrual/book-of-business-pipeline/actions/workflows/ci.yml/badge.svg)

An ELT pipeline that ingests advisor CRM records and market data into a layered
DuckDB warehouse, then runs declarative data quality checks against the results.
The CRM source is synthetic and seeded with known defects so that every check can
be verified against a manifest of exactly what was broken.

## Why

In wealth management, bad data rarely crashes anything. A holding tagged with the
wrong currency still produces a market value; it's just overstated by the FX rate.
An orphaned holding still sits in the database; it just never rolls up to a client.
This project is built around catching that class of silent error: every defect is
one that would produce plausible-looking output while being wrong.

## Architecture

```
Sources          synthetic CRM (clients, advisors, holdings) · Bank of Canada USD/CAD · synthetic prices
   │
Raw              every CSV landed as text, untouched
   │
Staging          typed, trimmed, deduplicated by rank, annotated with validity flags
   │
Core             dim_client · dim_advisor · fct_holding (FX-converted market value)
   │
Data quality     14 checks from YAML → dq.dq_results → non-zero exit on critical failure
```

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash run.sh        # generate → extract → load → transform → check
pytest -v
```

`run.sh` exits 1. That's correct: the seeded data contains critical defects by design,
and the DQ engine is doing its job by failing the run.

## Data quality checks

Checks live in `config/dq_checks.yml` as data, not code. Each is a SQL query that
returns one row per failure with a `failing_key` column; zero rows means pass.
Adding a check means adding a YAML entry, not writing Python.

Current run against the seeded data:

| Check | Severity | Failing | What it protects against |
|---|---|---|---|
| `client_id_unique` | critical | 12 | Duplicate records inflate AUM and split a client's holdings |
| `client_email_present` | warning | 18 | Clients who can't receive statements |
| `client_postal_code_valid` | warning | 14 | Broken mail delivery and provincial tax reporting |
| `client_dob_not_future` | critical | 7 | Corrupt entry; breaks age-based suitability rules |
| `holding_client_fk` | critical | 15 | Assets under management that roll up to no client |
| `holding_currency_consistent` | critical | 22 | Market value misstated by ~40% via the FX rate |
| `holding_quantity_positive` | critical | 9 | Negative positions corrupting portfolio totals |

Seven further checks (advisor integrity, holding uniqueness, valuation coverage,
FX freshness and plausibility, price coverage, row-count bounds) currently pass.
Checks that pass are what make the failures meaningful.

Every run appends to `dq.dq_results` rather than replacing it, so quality can be
tracked over time.

## Design decisions

**Raw is loaded as text.** `read_csv_auto(..., all_varchar = true)` skips type
inference. A malformed date either crashes an inferring load or gets silently
coerced to NULL; either way the defect disappears before anything can check it.
Typing happens in staging with `try_cast`, which returns NULL instead of aborting.

**Staging annotates; core decides.** Staging keeps all 612 client rows and labels
each with a `dedupe_rank`. Core keeps rank 1. The duplicates stay countable upstream,
which is why `client_id_unique` reads from staging.

**Deduplication ranks by data quality.** There's no `updated_at` to prefer the newest
record, so rows with an email beat rows without, valid postal codes beat invalid ones,
and name breaks remaining ties deterministically.

**Every join in the fact table is a LEFT JOIN.** An inner join would silently drop the
orphaned holdings and the check would never see them. A row that fails a rule has to
survive in order to be counted.

**FX is forward-filled across non-business days.** The Bank of Canada publishes no
rate on weekends. Staging generates a full calendar and carries the last real rate
forward, with an `is_carried_forward` flag so inferred values are never mistaken for
published ones.

**A check that errors is not a check that passes.** Malformed SQL or a missing table
reports `error`, distinct from `pass` and `fail`. A monitor that reports green when
it's broken is worse than no monitor.

**CI does not gate on the data quality step.** Lint and tests fail the build. The
pipeline runs for real on every push. The DQ step runs with `|| true`, because the
seeded defects make it fail every time by design, and a permanently red badge tells
a reviewer nothing. Its output is still in the logs.

## Bugs the tests caught

**NULL is not false.** The postal code check initially found 10 of 14 bad codes. An
empty CSV field loads as NULL, `regexp_matches(NULL, ...)` returns NULL, and
`NOT NULL` is NULL rather than true, so four missing postal codes were uncounted.
Fixed with an explicit `IS NOT NULL` and pinned by
`test_null_postal_code_is_invalid_not_unknown`.

**The dedupe picked the wrong row.** A NULL in a boolean sort key made the ranking
fall through to the name tiebreaker, where `'ANN'` sorts before `'Ann'` in ASCII,
so the duplicate *without* an email won. Caught by
`test_dedupe_prefers_row_with_email`; fixed by replacing boolean sort keys with
explicit `CASE` expressions that can't be NULL.

**Every holding valued at NULL.** Holdings were dated on a Saturday, which has no
price. Nothing errored; total AUM was silently NaN. That's now covered by the
`holding_valued` check.

## Testing

17 tests across three files, all against in-memory DuckDB so they never touch the
real warehouse:

- `test_generate_crm.py`: clean data is actually clean, generation is deterministic,
  and the defect manifest matches the rows actually broken
- `test_transforms.py`: each staging rule on hand-written input, including
  regression tests for both bugs above
- `test_dq.py`: config validity, that checks catch injected failures, that broken
  SQL reports an error, and that only critical failures fail the run

## What's real and what isn't

- **USD/CAD rates are live** from the Bank of Canada Valet API, with retry and
  exponential backoff, falling back to a cached snapshot if the API is unreachable.
- **CRM data and security prices are synthetic.** Prices are a seeded geometric
  random walk. This keeps the pipeline deterministic so tests can assert exact results.
- **DuckDB stands in for a cloud warehouse.** Same SQL dialect family and columnar
  model as Snowflake, with no infrastructure. It is not Snowflake.
- **No orchestration.** `run.sh` runs the stages in order. A scheduler would be the
  next step, not something this project needed.

## Structure

```
config/dq_checks.yml     check definitions
sql/staging/             typing, trimming, dedup ranking, FX forward-fill
sql/core/                dimensional model and FX-converted fact table
src/pipeline/            generate, extract, load, transform, dq
tests/                   pytest suite
run.sh                   end-to-end runner
```
