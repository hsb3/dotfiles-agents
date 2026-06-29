# DLT Production Patterns: Advanced Guide

This document provides production-ready patterns and solutions to common real-world challenges when using dlt for data pipelines.

## Table of Contents
1. [Custom Transformers with Metadata Enrichment](#1-custom-transformers-with-metadata-enrichment)
2. [Elegant DLT Patterns and Anti-Patterns](#2-elegant-dlt-patterns-and-anti-patterns)
3. [Production-Grade Error Handling](#3-production-grade-error-handling-with-retry-logic)
4. [Configuration Management](#4-production-configuration-management)
5. [Performance Optimization for Large Files](#5-performance-optimization-for-large-files)
6. [Safe Testing Patterns](#6-safe-testing-pattern-with-schema-isolation)

## 1. Custom Transformers with Metadata Enrichment

### Problem
Production data pipelines need audit trails and lineage information. Every row should be traceable to its source file, load time, and contain extracted metadata from filenames.

### Solution
```python
import dlt
import csv
import re
from datetime import datetime
from dlt.sources.filesystem import filesystem

@dlt.transformer
def enrich_with_metadata(file_items):
    """
    Transform CSV data by adding metadata for audit trails.
    Critical for production data lineage and troubleshooting.
    """
    for file_item in file_items:
        if isinstance(file_item, dict) and "file_name" in file_item:
            # Extract metadata from FileItem
            filename = file_item["file_name"]

            # Extract year from filename (common pattern for dated files)
            year_match = re.search(r'(19|20)\d{2}', filename)
            year = year_match.group(0) if year_match else "unknown"

            # Direct CSV reading - clean and reliable
            with file_item.open(mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Enrich each row with metadata
                    row["source_filename"] = filename
                    row["loaded_at"] = datetime.now().isoformat()
                    row["year"] = year
                    yield row

# Usage in pipeline - clean composition
def csv_with_lineage(data_dir="./data"):
    file_source = filesystem(
        bucket_url=data_dir,
        file_glob="*.csv"
    )

    # Apply transformer and configure
    enriched = file_source | enrich_with_metadata
    enriched = enriched.with_name("data_with_metadata")
    enriched.apply_hints(
        write_disposition="merge",
        merge_key=["id", "year"],
        primary_key=["id", "year"]
    )

    return enriched
```

### Why This Matters
- **Audit Compliance**: Every row can be traced to its source
- **Debugging**: Easy to identify problematic source files
- **Data Quality**: Track when data was loaded and from where

## 2. Elegant DLT Patterns and Anti-Patterns

Based on real-world experience, here are the key patterns that lead to clean, maintainable DLT code:

### ✅ **The Elegant Composition Pattern**

**Prefer:** Clean separation with pipe composition
```python
@dlt.transformer
def add_metadata(file_items):
    """Simple transformer - one responsibility"""
    import csv
    for file_item in file_items:
        filename = file_item["file_name"]
        with file_item.open(mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["source_file"] = filename
                yield row

def my_resource():
    """Clean resource - compose simple pieces"""
    file_source = filesystem(bucket_url=path, file_glob="*.csv")
    enriched = file_source | add_metadata
    return enriched.with_name("my_table").apply_hints(
        merge_key=["id", "date"],
        write_disposition="merge"
    )
```

**Key Benefits:**
- Each component has one responsibility
- Easy to test and debug
- Composable and reusable
- Clear data flow: `filesystem -> transformer -> configuration`

### ❌ **Common Anti-Patterns That Break**

**Don't:** Call `read_csv()` inside transformers
```python
# This BREAKS with PipeNotBoundToData error
@dlt.transformer
def broken_transformer(file_item):
    from dlt.sources.filesystem import read_csv
    rows = list(read_csv(file_item))  # ❌ FAILS - pipe not bound
    # ... rest of logic never runs
```

**Don't:** Complex monolithic resources
```python
# Inelegant - mixing file discovery, parsing, transformation, and configuration
@dlt.resource(name="complex", merge_key=["id"], primary_key=["id"])
def complex_resource():
    # 50+ lines of:
    # - File discovery logic
    # - Error handling
    # - CSV parsing with custom readers
    # - Data transformation
    # - Context management
    # Hard to test, debug, or reuse
```

### ✅ **Correct File Reading in Transformers**

**Use standard Python libraries directly:**
```python
# Clean and reliable
with file_item.open(mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        yield process_row(row)
```

**Not DLT's read_csv pipe:**
```python
# This breaks when called from transformers
rows = list(read_csv(file_item))  # ❌ PipeNotBoundToData
```

### ✅ **Configuration Separation Pattern**

**Apply hints after transformation:**
```python
def clean_resource():
    base = filesystem(...) | my_transformer
    configured = base.with_name("final_name")
    configured.apply_hints(
        merge_key=["id", "date"],
        write_disposition="merge"
    )
    return configured
```

**Not in complex decorator parameters:**
```python
# Harder to read and modify
@dlt.transformer(
    name="complex_name",
    merge_key=["id", "date", "other"],
    primary_key=["id", "date", "other", "more"],
    write_disposition="merge",
    parallelized=True,
    some_other_config="value"
)
def overly_configured_transformer(items):
    # Logic gets lost in configuration noise
```

### Key Insight: Simplicity Scales

The elegant patterns may seem "longer" at first, but they scale much better:
- **Debugging**: Each piece can be tested independently
- **Modification**: Change one concern without affecting others
- **Reusability**: Transformers work with different file sources
- **Clarity**: Data flow is obvious: source → transform → configure

## 3. Production-Grade Error Handling with Retry Logic

### Problem
Database connections fail, timeouts occur, and temporary issues cause pipeline failures that should be retried automatically.

### Solution
```python
import time
import logging
from typing import List

logger = logging.getLogger(__name__)

def run_pipeline_with_retry(pipeline, data_source, max_retries: int = 3):
    """
    Production retry pattern with exponential backoff.
    Distinguishes between recoverable and terminal errors.
    """
    retry_delay = 5  # seconds

    # Transient errors that should trigger retries
    transient_errors = [
        "connection", "timeout", "refused", "temporarily unavailable",
        "too many connections", "deadlock", "server closed"
    ]

    for attempt in range(max_retries):
        try:
            load_info = pipeline.run(data_source)

            # Check for failed jobs in successful run
            if load_info.has_failed_jobs:
                failed_jobs = [
                    job for job in load_info.load_packages[0].jobs.values()
                    if job.failed_message
                ]

                # Analyze failure messages for transient issues
                is_transient = any(
                    any(err in str(job.failed_message).lower() for err in transient_errors)
                    for job in failed_jobs
                )

                if is_transient and attempt < max_retries - 1:
                    logger.warning(f"Transient error detected, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise RuntimeError(f"Pipeline failed: {[job.failed_message for job in failed_jobs]}")

            # Success - return load info
            return load_info

        except Exception as e:
            error_str = str(e).lower()
            is_transient = any(err in error_str for err in transient_errors)

            if is_transient and attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed with transient error: {e}")
                logger.info(f"Retrying in {retry_delay}s (attempt {attempt + 2}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(f"Fatal error after {attempt + 1} attempts: {e}")
                raise

# Usage
pipeline = dlt.pipeline("my_pipeline", destination="postgres")
load_info = run_pipeline_with_retry(pipeline, my_data_source)
```

### Why This Matters
- **Resilience**: Handles temporary network/database issues automatically
- **Cost Savings**: Prevents unnecessary pipeline re-runs
- **Smart Failures**: Fails fast on real errors, retries transient ones

## 4. Production Configuration Management

### Problem
Managing secrets, environment-specific settings, and avoiding configuration conflicts between different environments.

### Solution
```python
import os
import dlt
import logging

logger = logging.getLogger(__name__)

class ProductionConfig:
    """
    Production configuration management following dlt best practices.
    Separates secrets from config and provides sensible defaults.
    """

    @property
    def csv_directory(self) -> str:
        """CSV directory with environment override capability."""
        # Environment variable takes precedence
        if env_dir := os.getenv("CSV_DIRECTORY"):
            return env_dir

        try:
            # Then dlt config
            return dlt.config["sources.csv_directory"]
        except KeyError:
            # Fallback for development
            logger.warning("CSV directory not configured, using default")
            return "./data"

    @property
    def chunk_size(self) -> int:
        """Optimized chunk size for performance."""
        try:
            return dlt.config["extract.chunk_size"]
        except KeyError:
            # Default optimized for PostgreSQL
            return 50000

    @property
    def parallel_workers(self) -> int:
        """Number of parallel load workers."""
        try:
            return dlt.config["load.workers"]
        except KeyError:
            # Conservative default
            return 4

    @property
    def schema_name(self) -> str:
        """Target schema name."""
        try:
            return dlt.config["destination.postgres.schema"]
        except KeyError:
            return "staging"

# Configuration files structure:
# .dlt/secrets.toml - NEVER commit to version control
"""
[destination.postgres.credentials]
host = "prod-db.company.com"
port = 5432
database = "analytics"
username = "etl_user"
password = "secret_password"
"""

# .dlt/config.toml - Safe to commit
"""
[extract]
chunk_size = 50000

[load]
workers = 8

[sources]
csv_directory = "/data/incoming"

[destination.postgres]
schema = "staging"
"""

# Usage in pipeline
config = ProductionConfig()
pipeline = dlt.pipeline(
    "data_loader",
    destination="postgres",
    dataset_name=config.schema_name
)
```

### Why This Matters
- **Security**: Prevents secrets leakage to version control
- **Flexibility**: Environment-specific configurations without code changes
- **Maintainability**: Clear separation of concerns

## 5. Performance Optimization for Large Files

### Problem
Loading large CSV files (GBs) efficiently while managing memory usage and maximizing throughput.

### Solution
```python
import os
import glob
from typing import Optional
import dlt
from dlt.sources.filesystem import filesystem, read_csv

class PerformanceOptimizedLoader:
    """
    Adaptive loading strategy that balances memory usage with performance.
    Key insight: Large files need sequential processing, small files can be parallel.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir

    def get_processing_strategy(self, file_pattern: str) -> dict:
        """
        Determine optimal processing strategy based on file sizes.
        Production insight: Memory usage vs parallelism tradeoff.
        """
        files = glob.glob(os.path.join(self.data_dir, file_pattern))

        if not files:
            return {"files_per_page": 1, "chunk_size": 10000}

        # Analyze file sizes
        total_size = sum(os.path.getsize(f) for f in files)
        avg_size_mb = (total_size / len(files)) / (1024**2)

        print(f"Found {len(files)} files, avg size: {avg_size_mb:.1f} MB")

        if avg_size_mb > 500:  # Large files (>500MB each)
            return {
                "files_per_page": 1,      # Sequential processing
                "chunk_size": 50000,      # Large chunks for efficiency
                "dtype": str              # Avoid pandas dtype inference overhead
            }
        elif avg_size_mb > 50:   # Medium files
            return {
                "files_per_page": 2,      # Limited parallelism
                "chunk_size": 25000,
                "dtype": str
            }
        else:  # Small files
            return {
                "files_per_page": 10,     # High parallelism
                "chunk_size": 10000,
                "dtype": str
            }

    def create_optimized_source(self, file_pattern: str, table_name: str):
        """Create source with performance optimizations."""
        strategy = self.get_processing_strategy(file_pattern)

        # Memory-optimized filesystem source
        file_source = filesystem(
            bucket_url=self.data_dir,
            file_glob=file_pattern,
            files_per_page=strategy["files_per_page"]
        )

        # Optimized CSV reader
        csv_reader = read_csv(
            chunksize=strategy["chunk_size"],
            dtype=strategy.get("dtype"),
            on_bad_lines='skip',  # Skip malformed rows instead of failing
            low_memory=True       # Use chunking for large files
        )

        # Apply performance hints
        data_source = file_source | csv_reader
        data_source.apply_hints(
            table_name=table_name,
            write_disposition="merge",
            # Optimize write performance
            loader_file_format="parquet"  # Faster than CSV for large data
        )

        return data_source

# Usage
loader = PerformanceOptimizedLoader("/data/large_csvs")
source = loader.create_optimized_source("*.csv", "my_table")

pipeline = dlt.pipeline("fast_loader", destination="postgres")
load_info = pipeline.run(source)
```

### Why This Matters
- **Memory Management**: Prevents OOM errors on large files
- **Throughput**: Maximizes processing speed based on file characteristics
- **Adaptive**: Automatically adjusts strategy based on data

## 6. Safe Testing Pattern with Schema Isolation

### Problem
Testing pipelines safely without affecting production data or schemas, while ensuring tests are realistic.

### Solution
```python
import dlt
from typing import Optional

class SafeTestPipeline:
    """
    Testing pattern that isolates test runs from production.
    Critical for safe CI/CD and development workflows.
    """

    def __init__(self, base_pipeline_name: str):
        self.base_pipeline_name = base_pipeline_name
        self.test_schema = "test_schema"

    def create_test_pipeline(self, test_name: Optional[str] = None):
        """
        Create isolated test pipeline with separate schema.
        Each test gets its own namespace to prevent conflicts.
        """
        pipeline_name = f"{self.base_pipeline_name}_test"
        if test_name:
            pipeline_name += f"_{test_name}"

        return dlt.pipeline(
            pipeline_name=pipeline_name,
            destination="postgres",
            dataset_name=self.test_schema,  # Isolated schema
            dev_mode=True  # Enable development features
        )

    def load_test_data(
        self,
        data_source,
        limit_rows: int = 100,
        cleanup: bool = True
    ):
        """
        Load limited test data with optional cleanup.
        """
        pipeline = self.create_test_pipeline()

        # Apply test-specific configuration
        if hasattr(data_source, 'apply_hints'):
            data_source.apply_hints(
                # Test-specific optimizations
                loader_file_format="insert_values",  # Fast for small data
                write_disposition="replace"  # Clean slate each test
            )

        # Load limited data
        print(f"🧪 Loading test data (limit: {limit_rows} rows)")

        # For sources that support row limiting
        if hasattr(data_source, 'add_limit'):
            data_source = data_source.add_limit(limit_rows)

        load_info = pipeline.run(data_source)

        # Verify test load
        with pipeline.sql_client() as client:
            result = client.execute_sql(
                f"SELECT COUNT(*) FROM {self.test_schema}.{data_source.name}"
            )
            row_count = result[0][0] if result else 0
            print(f"✅ Loaded {row_count:,} test rows")

        # Optional cleanup for CI environments
        if cleanup:
            self.cleanup_test_data(pipeline)

        return load_info

    def cleanup_test_data(self, pipeline):
        """Clean up test data after test completion."""
        try:
            with pipeline.sql_client() as client:
                client.execute_sql(f"DROP SCHEMA IF EXISTS {self.test_schema} CASCADE")
            print("🧹 Test data cleaned up")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

# Usage in tests
def test_my_pipeline():
    test_runner = SafeTestPipeline("my_data_pipeline")

    # Create test data source
    test_source = create_my_data_source()

    # Run test with isolation
    load_info = test_runner.load_test_data(
        test_source,
        limit_rows=50,
        cleanup=True
    )

    assert not load_info.has_failed_jobs
    # Additional assertions...

# Integration with pytest
import pytest

@pytest.fixture
def test_pipeline():
    return SafeTestPipeline("integration_test")

def test_full_pipeline(test_pipeline):
    """Integration test with proper isolation."""
    source = my_production_source()
    load_info = test_pipeline.load_test_data(source, limit_rows=1000)

    # Test passes/fails without affecting production
    assert load_info.jobs_count > 0
```

### Why This Matters
- **Safety**: Complete isolation from production data
- **Speed**: Test with small data subsets
- **CI/CD Ready**: Automatic cleanup for continuous integration
