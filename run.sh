#!/usr/bin/env bash
set -euo pipefail

echo "==> generating source data"
python -m src.pipeline.generate_crm

echo "==> extracting external data"
python -m src.pipeline.extract

echo "==> loading raw layer"
python -m src.pipeline.load

echo "==> building warehouse models"
python -m src.pipeline.transform

echo "==> running data quality checks"
python -m src.pipeline.dq