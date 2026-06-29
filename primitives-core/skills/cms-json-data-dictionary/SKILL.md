---
name: cms-json-data-dictionary
description: Create comprehensive machine-readable JSON data dictionaries from CMS markdown documentation. Use after converting PDFs to markdown (cms-pdf-to-markdown skill), when building BigQuery ETL pipelines, when documenting dataset schemas, or when need structured metadata for data warehouses. Captures all variables, constraints, validation rules, special values (suppression *, missing .), FIPS codes, person-years, and CMS-specific patterns. Output is used by cms-bigquery-etl-generator skill.
---

# CMS JSON Data Dictionary Generator

Create machine-readable JSON data dictionaries from CMS markdown documentation.

## Input

**Markdown data dictionary** from cms-pdf-to-markdown:
- `{external_root}/{dataset}/processing/data_dictionary_v_pdf_skill.md`
- Must have: Variable definitions table, file parameters, notes

## Process

1. Parse markdown tables (variable definitions, parameters)
2. Infer data types using CMS patterns
3. Extract constraints (year ranges, field lengths, patterns)
4. Document special values (`*` = suppressed, `.` = missing)
5. Create JSON with all metadata sections

## Data Type Inference

```python
# CMS-specific patterns
if "year" in name and "person" not in desc: "integer"
elif "psn_yrs" in name: "float"  # Person-years are fractional
elif name in ["Tot_AB"]: "integer"  # Counts
elif "id" in name.lower(): "string"  # Preserve leading zeros
else: "string"  # Safe default
```

## JSON Structure

```json
{
  "metadata": {"title": "...", "program": "...", ...},
  "variables": [
    {
      "variable_name": "State_ID",
      "data_type": "string",
      "required": true,
      "constraints": {"length": 2, "pattern": "^[0-9]{2}$"},
      "special_values": {"*": "Suppressed", ".": "Missing"}
    }
  ],
  "data_quality": {"suppression_rules": {...}},
  "file_parameters": [...],
  "notes": [...],
  "references": [...]
}
```

## CMS Patterns

**FIPS codes** (preserve leading zeros):
```json
{"variable_name": "State_ID", "data_type": "string", "constraints": {"length": 2}}
{"variable_name": "County_ID", "data_type": "string", "constraints": {"length": 3}}
```

**Person-years** (fractional enrollment):
```json
{"variable_name": "AB_Psn_Yrs_ESRD", "data_type": "float", "unit": "person-years"}
```

**Suppression** (HIPAA compliance):
```json
"special_values": {"*": "Suppressed (1-10 beneficiaries)"}
```

## Output

Primary: `{external_root}/{dataset}/processing/data_dictionary.json`
Copy to: `{external_root}/_config/data_dictionaries/{dataset}.json`

## Validation

```bash
# Verify JSON
python -c "import json; dd=json.load(open('data_dictionary.json')); print(f'{len(dd[\"variables\"])} variables')"

# Check required sections
python -c "import json; dd=json.load(open('data_dictionary.json')); assert all(k in dd for k in ['metadata','variables','data_quality'])"
```

## Example

ACO County dataset:
- Input: 7.4 KB markdown (5 pages, 4 tables)
- Output: 21 KB JSON
- Variables: 12
- Enrollment types: 4 (ESRD, DISABLED, AGED/DUAL, AGED/NON-DUAL)
- File years: 12 (2014-2024)
- Notes: 8 with hyperlinks

Next: Use with cms-bigquery-etl-generator to create ETL pipeline.
