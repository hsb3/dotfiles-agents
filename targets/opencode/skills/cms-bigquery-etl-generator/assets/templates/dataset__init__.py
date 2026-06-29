"""
{DATASET_TITLE} - ETL Pipeline for BigQuery

This package contains ETL scripts to load {PROGRAM_NAME} data to BigQuery.

Structure:
- config/: Configuration files
- src/: Source code (ETL, schema, validation)
- tests/: Test suite
- docs/: Additional documentation
- logs/: Runtime logs

Usage:
    # From this directory
    cd datasets/{dataset_code}
    uv run python src/load_to_bigquery.py

    # Or from project root
    uv run python -m datasets.{dataset_code}.src.load_to_bigquery

For more information, see README.md
"""

__version__ = "1.0.0"
__author__ = "CMS Data Mart Team"

# Public API - import from src
from .src import schema, validate

__all__ = ['schema', 'validate']
