---
name: cms-pdf-to-markdown
description: Convert CMS PDF documentation (data dictionaries, methodology documents, technical specifications) to clean markdown format using pdfplumber. Use when CMS releases new datasets with PDF documentation, when documentation updates are needed, or when version-controlled docs are required. Creates markdown files with preserved tables, structure, and hyperlinks for CMS data engineering workflows.
---

# CMS PDF to Markdown Converter

Convert CMS PDF documentation to markdown format for version control and further processing.

## When to Use

- CMS releases new dataset with PDF documentation
- Need to extract tables from CMS data dictionaries
- Creating machine-readable data dictionary (prerequisite)
- Version-controlling documentation

## Quick Start

```python
import pdfplumber

pdf_path = "docs/data_dictionary.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
```

## Process

1. **Extract content** with pdfplumber
2. **Convert tables** to markdown format with | delimiters
3. **Preserve multi-line cells** using `<br>` tags
4. **Convert links** to markdown format `[text](url)`
5. **Save** to `processing/` directory with `_v_pdf_skill.md` suffix

## Table Conversion

CMS data dictionaries have tables like:

| Term Name | Variable Name | Definition | Footnotes |
|-----------|---------------|------------|-----------|
| Year | Year | Calendar year... | For 2019... |

Multi-line cells use `<br>`:
```markdown
| Field | Value |
|-------|-------|
| Multi<br>line | Content<br>here |
```

## CMS-Specific Handling

- **Suppression indicators**: Preserve `*` and `.` in tables
- **FIPS codes**: Keep leading zeros in numeric codes
- **References**: Extract URLs and create markdown links
- **Notes**: Number and preserve with hyperlinks

## Output

Save to: `{external_root}/{dataset}/processing/{filename}_v_pdf_skill.md`

Naming pattern:
- `data_dictionary.pdf` → `data_dictionary_v_pdf_skill.md`
- `methodology.pdf` → `methodology_v_pdf_skill.md`

## Dependencies

```bash
uv add pdfplumber
```

## Example

From today's ACO County work:
- Input: `aco-county_data_dictionary.pdf` (177 KB, 5 pages)
- Output: `data_dictionary_v_pdf_skill.md` (7.4 KB)
- Tables extracted: 4 (variable definitions, parameters)
- Notes: 8 with hyperlinks

See reference implementation in processing/ directory.
