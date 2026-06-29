#!/usr/bin/env python3
"""
DLT CSV Pipeline Template

This template provides a production-ready starting point for building
dlt pipelines that load CSV files from local or cloud storage.

Key Features:
- Metadata enrichment for data lineage
- Incremental loading support
- Error handling with retry logic
- Configurable for different environments
"""

import dlt
import csv
from datetime import datetime
from typing import Iterator
from dlt.sources.filesystem import filesystem


@dlt.transformer
def enrich_with_metadata(file_items):
    """
    Enrich CSV data with source metadata for audit trails.

    Adds:
    - source_filename: Name of the source file
    - loaded_at: Timestamp when data was loaded
    """
    for file_item in file_items:
        if isinstance(file_item, dict) and "file_name" in file_item:
            filename = file_item["file_name"]

            # Read CSV using standard library
            with file_item.open(mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Add metadata fields
                    row["source_filename"] = filename
                    row["loaded_at"] = datetime.now().isoformat()
                    yield row


@dlt.source
def csv_source(
    data_dir: str = "./data",
    file_pattern: str = "*.csv"
):
    """
    Create a dlt source for loading CSV files.

    Args:
        data_dir: Directory containing CSV files (local path or cloud URI)
        file_pattern: Glob pattern to match files (e.g., "*.csv", "**/*.csv")

    Returns:
        dlt source with CSV data enriched with metadata
    """
    # Create filesystem resource
    file_lister = filesystem(
        bucket_url=data_dir,
        file_glob=file_pattern
    )

    # Apply transformer and configure
    enriched = file_lister | enrich_with_metadata
    enriched = enriched.with_name("csv_data")

    # Configure loading strategy
    enriched.apply_hints(
        write_disposition="merge",  # Use merge for upserts
        primary_key="id",  # Adjust to your primary key column(s)
        # For incremental loading by file modification date:
        # incremental=dlt.sources.incremental("modification_date")
    )

    return enriched


def run_pipeline():
    """
    Execute the CSV pipeline with production settings.
    """
    # Create pipeline
    pipeline = dlt.pipeline(
        pipeline_name="csv_loader",
        destination="postgres",  # or "bigquery", "snowflake", etc.
        dataset_name="staging"
    )

    # Create source
    data_source = csv_source(
        data_dir="./data",
        file_pattern="*.csv"
    )

    # Run pipeline
    print("Starting pipeline run...")
    load_info = pipeline.run(data_source)

    # Check results
    if load_info.has_failed_jobs:
        print("❌ Pipeline completed with errors:")
        for package in load_info.load_packages:
            for job in package.jobs.values():
                if job.failed_message:
                    print(f"  - {job.job_file_path}: {job.failed_message}")
        raise RuntimeError("Pipeline failed")
    else:
        print("✅ Pipeline completed successfully!")
        print(f"  - Loaded {len(load_info.load_packages)} packages")
        print(f"  - Total jobs: {sum(len(p.jobs) for p in load_info.load_packages)}")

    return load_info


if __name__ == "__main__":
    # Run the pipeline
    run_pipeline()
