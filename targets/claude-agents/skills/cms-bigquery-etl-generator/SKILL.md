---
name: cms-bigquery-etl-generator
description: Generate complete production-ready BigQuery ETL pipelines from JSON data dictionaries. Use after creating JSON data dictionary (cms-json-data-dictionary skill), when setting up new CMS dataset for BigQuery loading, or when need standardized ETL structure. Creates full package with schema, validation, transformation, config precedence, tests, and documentation following project conventions (uv, config inheritance, underscore naming, CMS patterns). Output is ready-to-use datasets/{name}/ directory.
---

# CMS BigQuery ETL Pipeline Generator

Generate complete ETL pipeline from JSON data dictionary.

## Input

**JSON data dictionary** from cms-json-data-dictionary:
- Location: `{external_root}/{dataset}/processing/data_dictionary.json`
- Must include: variables, data_quality, file_parameters sections

**Dataset information**:
```python
dataset_code = "aco_county"  # Underscore naming
external_path = "{external_root}/aco_county"
table_name = "aco_county_assigned_beneficiaries"
```

## Generated Package Structure

```
datasets/{dataset_name}/
├── config/
│   ├── config.yaml (minimal, uses precedence)
│   └── config.example.yaml
├── src/
│   ├── __init__.py
│   ├── config_loader.py (precedence handler)
│   ├── load_to_bigquery.py (ETL orchestration)
│   ├── schema.py (BigQuery schema)
│   └── validate.py (data validation)
├── tests/
│   ├── __init__.py
│   └── test_pipeline.py
├── docs/
│   └── SCRIPTS_OVERVIEW.md
├── logs/
│   └── .gitkeep
├── README.md (15 KB guide)
├── __init__.py
├── requirements.txt
└── pytest.ini
```

## Generation Process

### 1. BigQuery Schema (src/schema.py)

From JSON variables, generate:
```python
from google.cloud import bigquery

def get_table_schema():
    return [
        bigquery.SchemaField(
            "year", "INTEGER", mode="REQUIRED",
            description="From data dictionary"
        ),
        bigquery.SchemaField(
            "state_id", "STRING", mode="REQUIRED"  # String for leading zeros
        ),
        # ... all variables from JSON
    ]
```

**Type mapping**:
- JSON `"integer"` → BigQuery `INTEGER`
- JSON `"float"` → BigQuery `FLOAT64`
- JSON `"string"` → BigQuery `STRING`

**Mode**: `required: true` → `mode="REQUIRED"`, else `NULLABLE`

### 2. Validation (src/validate.py)

From JSON constraints, generate:
```python
def validate_year_range(df, min_year, max_year):
    """From file_parameters min/max year."""

def validate_state_county_ids(df):
    """From FIPS code constraints."""

def validate_person_year_consistency(df, tolerance):
    """CMS-specific: enrollment types sum to total."""
```

### 3. ETL Orchestrator (src/load_to_bigquery.py)

Generate ETL with:
- Config precedence loading
- CSV reading (preserve dtypes for FIPS codes)
- Transformation logic:
  ```python
  # Parse suppression/missing from special_values
  if value == '*': return None, True, False  # suppressed
  if value == '.': return None, False, True  # missing

  # Pad FIPS codes from constraints
  df['state_id'] = df['State_ID'].str.zfill(2)
  df['county_id'] = df['County_ID'].str.zfill(3)
  ```
- BigQuery loading with pyarrow
- Pre/post load validation

### 4. Configuration (config/config.yaml)

Generate minimal config:
```yaml
bigquery:
  table_id: "{dataset}_table"

data_source:
  data_directory: "${storage.external_root}/{dataset}/data"
  file_pattern: "*.csv"
  data_dictionary: "${storage.external_root}/_config/data_dictionaries/{dataset}.json"

validation:
  min_year: {from file_parameters}
  max_year: {from file_parameters}

transformation:
  # Based on data dictionary patterns
  pad_state_id: true  # If State_ID found
  suppression_indicator: "*"  # From special_values
  missing_indicator: "."
```

Uses precedence - inherits project_id, logging from root.

### 5. Tests (tests/test_pipeline.py)

Generate 6 component tests:
1. Config loading (with precedence)
2. Data files accessible
3. Schema definition
4. Validation functions
5. BigQuery connection
6. Data transformation

### 6. Documentation (README.md)

Generate comprehensive guide with:
- Setup instructions (GCP, uv, dependencies)
- Usage examples
- Output schema description
- Example BigQuery queries
- Troubleshooting

## Project Conventions

**Use uv**:
```bash
uv add google-cloud-bigquery
uv run python src/load_to_bigquery.py
```

**Underscore naming**:
- Dataset codes: `aco_county` not `aco-county`
- Directories match codes
- Python modules: snake_case

**Config precedence**:
- Include `src/config_loader.py` from assets/templates/
- Dataset config inherits from `../../config.yaml`
- Use `${storage.external_root}` variables

**CMS patterns**:
- Suppression: `*` → NULL + boolean flag
- Missing: `.` → NULL + boolean flag
- FIPS codes: String type, zero-padded
- Person-years: FLOAT64 type

## Templates

Use templates from `assets/templates/`:
- `config_loader.py` - Config precedence handler
- `__init__.py` - Package initialization
- `.gitignore` - Standard ignores for logs/

Copy and customize for each dataset.

## Example

ACO County (reference implementation):
- Input: 21 KB JSON (12 variables)
- Generated: 11 files, 1,943 lines of code
- Tests: 5/6 passing
- Load status: 531,289 records loaded successfully
- Location: `datasets/aco_county/`

Use as template for new datasets.

## Usage

```bash
# After JSON dictionary created
cd datasets
# Generate new dataset package
# ... (run this skill)

# Test
cd {dataset_name}
uv run python tests/test_pipeline.py

# Load
uv run python src/load_to_bigquery.py
```

## Verification

After generation:
- [ ] All 11+ files created
- [ ] Imports work: `from datasets.{dataset}.src import schema`
- [ ] Config loads: `python src/config_loader.py`
- [ ] Tests pass: 5/6 minimum
- [ ] README comprehensive

See `assets/templates/` for code templates.
