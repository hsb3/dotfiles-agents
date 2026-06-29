# DLT CLI Reference Guide

Essential DLT CLI commands for managing and inspecting data pipelines.

## Pipeline Inspection

### View Pipeline Information
```bash
# Basic pipeline info
dlt pipeline <pipeline_name> info

# Detailed pipeline info with source states
dlt pipeline <pipeline_name> info --verbose
```

### Launch Streamlit Data Explorer
```bash
# Interactive data exploration and pipeline inspection
dlt pipeline <pipeline_name> show
```
**What it does:**
- Launches a Streamlit web app (usually at http://localhost:8501)
- Shows pipeline run history and statistics
- Allows browsing target database tables
- Displays schema evolution and data samples
- Provides SQL query interface for data

### View Pipeline Run History
```bash
# Show execution traces
dlt pipeline <pipeline_name> trace

# Show detailed trace with verbose output
dlt pipeline <pipeline_name> trace --verbose
```

## Schema Management

### Export Current Schema
```bash
# Export schema to JSON
dlt pipeline <pipeline_name> schema

# Export schema to YAML (more readable)
dlt pipeline <pipeline_name> schema --format yaml

# Save schema to file
dlt pipeline <pipeline_name> schema --format yaml > schema_backup.yaml
```

## State Management

### View Pipeline State
```bash
# Show current pipeline state
dlt pipeline <pipeline_name> info

# Show detailed state information
dlt pipeline <pipeline_name> info --verbose
```

### Drop Pipeline Data
```bash
# Drop specific tables and reset state
dlt pipeline <pipeline_name> drop <resource_name>

# Drop all pipeline data (interactive confirmation)
dlt pipeline <pipeline_name> drop --drop-all

# Drop multiple resources using regex
dlt pipeline <pipeline_name> drop "re:^repo"
```

### Sync Pipeline from Destination
```bash
# Restore pipeline state from destination
dlt pipeline <pipeline_name> sync

# Sync when local state is missing
dlt pipeline <pipeline_name> sync --destination postgres --dataset-name my_dataset
```

## Data Exploration

### Query Target Database
```bash
# Run SQL queries against the target database
dlt pipeline <pipeline_name> sql "SELECT COUNT(*) FROM my_table"

# Complex queries
dlt pipeline <pipeline_name> sql "
SELECT
    year,
    COUNT(*) as records
FROM my_table
GROUP BY year
ORDER BY year"
```

## Pipeline Maintenance

### Clean Up Pipeline Artifacts
```bash
# Remove processed load packages
dlt pipeline <pipeline_name> drop-pending-packages

# List all pipelines
dlt pipeline --list-pipelines
```

### View Failed Jobs
```bash
# Show failed jobs with error messages
dlt pipeline <pipeline_name> failed-jobs
```

### View Load Package Details
```bash
# Show details of a specific load package
dlt pipeline <pipeline_name> load-package <load_id>

# Show most recent load package
dlt pipeline <pipeline_name> load-package
```

## Initialization Commands

### Initialize New Pipeline
```bash
# Initialize pipeline with source and destination
dlt init <source_name> <destination_name>

# List available verified sources
dlt init --list-sources

# List available destinations
dlt init --list-destinations

# Eject source code for customization
dlt init <source_name> <destination_name> --eject
```

## Global Options

### Telemetry Control
```bash
# Disable telemetry
dlt --disable-telemetry <command>

# Enable telemetry
dlt --enable-telemetry <command>

# Check telemetry status
dlt telemetry
```

### Debug Mode
```bash
# Run command with full stack traces
dlt --debug pipeline <pipeline_name> info
```

### Non-Interactive Mode
```bash
# Run command without prompts (for CI/CD)
dlt --non-interactive pipeline <pipeline_name> drop my_resource
```

## Common Workflows

### Development Workflow
```bash
# 1. Initialize pipeline
dlt init my_source postgres

# 2. Run pipeline
python my_pipeline.py

# 3. Inspect results
dlt pipeline my_pipeline show

# 4. Check for issues
dlt pipeline my_pipeline trace

# 5. Query data
dlt pipeline my_pipeline sql "SELECT * FROM my_table LIMIT 5"
```

### Production Monitoring
```bash
# Check pipeline health
dlt pipeline my_pipeline info

# Monitor for failures
dlt pipeline my_pipeline failed-jobs

# Verify data freshness
dlt pipeline my_pipeline sql "
SELECT
    MAX(_dlt_load_id) as latest_load,
    COUNT(*) as total_records
FROM my_table"
```

### Troubleshooting
```bash
# Show detailed error information
dlt pipeline my_pipeline trace --verbose

# Check for failed jobs
dlt pipeline my_pipeline failed-jobs

# View load package contents
dlt pipeline my_pipeline load-package <load_id>
```

## Advanced Features

### Schema Validation
```bash
# Validate schema file
dlt schema path/to/schema.yaml

# Convert schema format
dlt schema path/to/schema.yaml --format json

# Remove default values from schema output
dlt schema path/to/schema.yaml --remove-defaults
```

### Deployment
```bash
# Deploy to GitHub Actions
dlt deploy my_pipeline.py github-action --schedule "*/30 * * * *"

# Deploy to Airflow Composer
dlt deploy my_pipeline.py airflow-composer

# Deploy options
dlt deploy my_pipeline.py github-action --schedule "0 * * * *" --run-manually --run-on-push
```

## Configuration Tips

### Pipeline Directory
```bash
# Specify custom pipelines directory
dlt pipeline --pipelines-dir /path/to/pipelines my_pipeline info
```

### Verbose Output
```bash
# Get more detailed output
dlt pipeline -v my_pipeline info

# Even more verbose
dlt pipeline -vv my_pipeline info
```

## Best Practices

### 🔍 **Regular Health Checks**
```bash
# Daily health check script
#!/bin/bash
echo "=== Pipeline Health Check ==="
dlt pipeline my_pipeline info
echo "=== Recent Errors ==="
dlt pipeline my_pipeline trace | grep -i error | tail -5
echo "=== Data Volume Check ==="
dlt pipeline my_pipeline sql "SELECT COUNT(*) FROM my_table"
```

### 🛡️ **Safe State Management**
- Always review what will be dropped before confirming
- Back up schemas before major changes: `dlt pipeline my_pipeline schema > backup.yaml`
- Test state resets in development first

### 🚀 **Performance Monitoring**
- Use `show` command to visualize performance trends
- Monitor load package sizes and processing times
- Check for growing pipeline state that might indicate memory leaks

## Environment Setup

Ensure you're using the correct environment:
```bash
# Activate virtual environment
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows

# All dlt commands use the active environment
dlt pipeline my_pipeline info
```

The DLT CLI automatically discovers pipeline configuration from your project's `.dlt/` directory and environment variables.
