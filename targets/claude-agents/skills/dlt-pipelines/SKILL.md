---
name: dlt-pipelines
description: Build production-ready ETL/ELT data pipelines using dlt (data load tool), a Python framework for loading data from various sources to data warehouses. Use this skill when building new pipelines, debugging existing pipelines with CLI commands, optimizing performance, or implementing best practices for configuration management, schema evolution, incremental loading, and error handling. The skill covers filesystem sources (CSV, Parquet, JSON), database sources, API sources, and destinations like PostgreSQL, BigQuery, Snowflake, and DuckDB.
---

# DLT Pipelines Skill

Build robust, production-ready data pipelines using dlt (data load tool), a Python ETL framework that simplifies loading data from diverse sources to modern data warehouses.

## When to Use This Skill

Use this skill when:
- Building new ETL/ELT pipelines to load data from files, APIs, or databases
- Debugging pipeline issues using dlt CLI commands (`dlt pipeline <name> info`, `trace`, `show`)
- Optimizing pipeline performance for large-scale data loads
- Implementing incremental loading patterns to process only new/changed data
- Managing configuration separation (secrets.toml vs config.toml)
- Setting up proper error handling with retry logic
- Working with schema evolution and schema contracts
- Troubleshooting failed jobs or investigating pipeline state

## Core Concepts

### Configuration Architecture

dlt uses a two-file configuration system for security and portability:

**`.dlt/secrets.toml`** - SENSITIVE credentials (NEVER commit to git):
- Database passwords, API keys, authentication tokens
- Cloud storage credentials
- Production: use environment variables instead of hardcoding

**`.dlt/config.toml`** - NON-SENSITIVE settings (safe to commit):
- Database hostnames, file paths, timeouts
- Performance tuning parameters (workers, chunk sizes)
- Feature flags and processing options

**CRITICAL: Avoid Key Collisions**
Never use identical section names in both files. Use nested structure:
```toml
# secrets.toml
[sources.my_source.credentials]
api_key = "secret"

# config.toml
[sources.my_source.config]
batch_size = 1000
```

### Write Dispositions

Choose the right loading strategy:

- **`replace`**: Full table refresh (TRUNCATE + INSERT)
  - Use for: Complete snapshots, dimension tables
  - Idempotent: Yes

- **`append`**: Add all new rows (INSERT)
  - Use for: Event logs, immutable data
  - Idempotent: No (reruns create duplicates)

- **`merge`**: Intelligent upsert/update (DELETE + INSERT or UPSERT)
  - Use for: Stateful data that changes over time
  - Requires: `primary_key` and/or `merge_key` hints
  - Idempotent: Yes
  - Strategies: `delete-insert` (default) or `upsert` (faster for large tables)

### Schema Management

**Schema Inference**: dlt automatically creates tables and infers types on first run.

**Schema Evolution**: New columns are automatically added on subsequent runs.

**Schema Contracts**: Control how schema changes are handled:
- `evolve` (default): Allow new columns
- `freeze`: Reject any schema changes (recommended for production)
- `discard_value`: Load row but set new columns to NULL
- `discard_row`: Reject rows with unexpected columns

**Best Practice**: Use explicit hints for production:
```python
resource.apply_hints(
    primary_key="id",
    columns={"created_at": {"data_type": "timestamp", "nullable": False}}
)
```

### Incremental Loading

Process only new or changed data to improve efficiency:

**Cursor-based**: Track last processed value (timestamp, ID)
```python
@dlt.resource(primary_key="id", write_disposition="merge")
def my_resource(
    updated_at=dlt.sources.incremental("updated_at", initial_value="1970-01-01")
):
    yield from api.get_items(updated_after=updated_at.last_value)
```

**File-based**: Track modification dates or processed filenames
```python
# By modification date
filesystem(..., incremental=dlt.sources.incremental("modification_date"))

# By filename tracking (more robust)
processed = dlt.current.resource_state().setdefault("processed_files", [])
if filename not in processed:
    # Process file
    processed.append(filename)
```

## How to Use This Skill

### 1. Reference Documentation

The skill includes comprehensive reference documentation:

**Read `references/dlt_comprehensive_guide.md` for:**
- Project initialization and setup
- Configuration best practices (config.toml vs secrets.toml)
- CSV ingestion patterns with filesystem source
- Write disposition strategies (replace, append, merge)
- Schema management and governance
- Performance optimization techniques
- Incremental loading patterns
- Production monitoring and error handling

**Read `references/dlt_production_patterns.md` for:**
- Custom transformers with metadata enrichment
- Elegant patterns vs anti-patterns (what works, what breaks)
- Production-grade error handling with retry logic
- Configuration management classes
- Performance optimization for large files
- Safe testing patterns with schema isolation

**Read `references/dlt_cli_reference.md` for:**
- Pipeline inspection commands (`info`, `show`, `trace`)
- Schema management commands
- State management and synchronization
- Troubleshooting failed jobs
- Data exploration queries
- Deployment options

### 2. Use Template Files

**Start new pipelines** using `scripts/csv_pipeline_template.py`:
- Production-ready CSV loading with metadata enrichment
- Proper error checking and logging
- Configurable for different environments

**Implement production patterns** using `scripts/production_helpers.py`:
- `run_with_retry()`: Automatic retry with exponential backoff
- `ProductionConfig`: Environment variable and config management
- `TestPipeline`: Isolated testing without affecting production
- `monitor_schema_changes()`: Track schema drift

**Configure projects** using template files in `assets/`:
- `config.toml.template`: Non-sensitive settings template
- `secrets.toml.template`: Credentials template (with examples)

### 3. Common Workflows

#### Initialize New Pipeline
```bash
# Create project structure
dlt init <source> <destination>

# Copy and customize configuration templates from assets/
cp assets/config.toml.template .dlt/config.toml
cp assets/secrets.toml.template .dlt/secrets.toml

# Edit configuration files
# Add credentials to .dlt/secrets.toml
# Add settings to .dlt/config.toml
```

#### Build Custom Pipeline
```python
# Use template as starting point
# See scripts/csv_pipeline_template.py

import dlt
from scripts.production_helpers import run_with_retry

# Define source
@dlt.source
def my_source():
    # Implement extraction logic
    pass

# Create and run pipeline
pipeline = dlt.pipeline("my_pipeline", destination="postgres")
load_info = run_with_retry(pipeline, my_source())
```

#### Debug Pipeline Issues
```bash
# Check pipeline status
dlt pipeline my_pipeline info

# View detailed trace
dlt pipeline my_pipeline trace --verbose

# Inspect failed jobs
dlt pipeline my_pipeline failed-jobs

# Launch interactive explorer
dlt pipeline my_pipeline show

# Query data directly
dlt pipeline my_pipeline sql "SELECT COUNT(*) FROM my_table"
```

#### Optimize Performance

For large data loads, configure file rotation and parallelism in `.dlt/config.toml`:
```toml
[normalize]
workers = 7  # CPU cores - 1

[load]
workers = 20  # Can increase if DB handles it

[data_writer]
file_max_items = 100000  # Enable file rotation
file_max_bytes = 10485760  # 10MB chunks
```

**Database-side**: Create indexes on merge keys for large tables:
```sql
CREATE INDEX idx_my_table_merge_key ON my_table(date_column);
CREATE INDEX idx_my_table_pk ON my_table(id_column);
```

## Best Practices

### ✅ Do This

1. **Separate secrets from config** using nested structures to avoid key collisions
2. **Use explicit schema hints** for production pipelines (not just inference)
3. **Implement retry logic** for transient errors (network, database timeouts)
4. **Enable file rotation** for large data loads to unlock parallelism
5. **Set schema contracts to `freeze`** for production tables
6. **Monitor schema changes** using `LoadInfo` object inspection
7. **Use incremental loading** to process only new/changed data
8. **Create database indexes** on merge_key and primary_key columns

### ❌ Avoid This

1. **Don't call `read_csv()` inside transformers** - use standard Python `csv` library
2. **Don't use identical section names** in secrets.toml and config.toml
3. **Don't hardcode credentials** in secrets.toml - use environment variables
4. **Don't skip error checking** - always inspect `LoadInfo.has_failed_jobs`
5. **Don't create monolithic resources** - use composition pattern
6. **Don't ignore schema contracts** - enforce governance in production
7. **Don't reprocess all data** - implement incremental patterns
8. **Don't forget database indexes** when using merge disposition

## Elegant Pattern: Composition Over Complexity

Build pipelines by composing simple, single-responsibility components:

```python
# ✅ Clean composition pattern
@dlt.transformer
def add_metadata(file_items):
    """Single responsibility: add metadata"""
    for item in file_items:
        # Simple, testable logic
        yield enrich_row(item)

def my_pipeline():
    """Compose components"""
    source = filesystem(...) | add_metadata
    return source.with_name("table").apply_hints(
        merge_key="id",
        write_disposition="merge"
    )
```

This approach provides:
- **Debuggability**: Test each component independently
- **Reusability**: Transformers work with different sources
- **Clarity**: Data flow is obvious
- **Maintainability**: Change one component without affecting others

## Troubleshooting Guide

**Pipeline fails with connection errors:**
→ Use `run_with_retry()` from production_helpers.py

**Schema keeps changing unexpectedly:**
→ Set schema contract to `freeze` and monitor with `monitor_schema_changes()`

**Performance is slow for large files:**
→ Enable file rotation in config.toml (`file_max_items`, `file_max_bytes`)

**Config values not loading:**
→ Check for key collisions between secrets.toml and config.toml

**Merge is slow on large tables:**
→ Create database indexes on merge_key and primary_key columns

**PipeNotBoundToData error:**
→ Don't call `read_csv()` in transformers; use Python `csv.DictReader`

**Duplicates after rerun:**
→ Use `merge` disposition with proper primary_key instead of `append`

## Additional Resources

Consult the reference documentation for detailed information on specific topics:
- **Comprehensive Guide**: Architecture, best practices, all major features
- **Production Patterns**: Real-world solutions to common challenges
- **CLI Reference**: Complete command reference for pipeline management

Use template files in `scripts/` and `assets/` as starting points for new pipelines or to implement common patterns.

