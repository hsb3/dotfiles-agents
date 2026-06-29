# Notion Filters and Sorts Reference

Used in `notion.databases.query()`.

---

## Table of Contents
- [Filter Structure](#filter-structure)
- [Property Filters](#property-filters)
- [Compound Filters](#compound-filters)
- [Sorts](#sorts)
- [Complete Examples](#complete-examples)

---

## Filter Structure

Basic filter structure:
```python
{
    "property": "Property Name",
    "property_type": {
        "condition": "value"
    }
}
```

---

## Property Filters

### title / rich_text
```python
{"property": "Name", "title": {"equals": "Exact match"}}
{"property": "Name", "title": {"does_not_equal": "Not this"}}
{"property": "Name", "title": {"contains": "substring"}}
{"property": "Name", "title": {"does_not_contain": "substring"}}
{"property": "Name", "title": {"starts_with": "prefix"}}
{"property": "Name", "title": {"ends_with": "suffix"}}
{"property": "Name", "title": {"is_empty": True}}
{"property": "Name", "title": {"is_not_empty": True}}

# Same conditions for rich_text
{"property": "Description", "rich_text": {"contains": "bug"}}
```

### number
```python
{"property": "Price", "number": {"equals": 100}}
{"property": "Price", "number": {"does_not_equal": 100}}
{"property": "Price", "number": {"greater_than": 50}}
{"property": "Price", "number": {"less_than": 50}}
{"property": "Price", "number": {"greater_than_or_equal_to": 50}}
{"property": "Price", "number": {"less_than_or_equal_to": 50}}
{"property": "Price", "number": {"is_empty": True}}
{"property": "Price", "number": {"is_not_empty": True}}
```

### checkbox
```python
{"property": "Done", "checkbox": {"equals": True}}
{"property": "Done", "checkbox": {"equals": False}}
```

### select
```python
{"property": "Status", "select": {"equals": "In Progress"}}
{"property": "Status", "select": {"does_not_equal": "Done"}}
{"property": "Status", "select": {"is_empty": True}}
{"property": "Status", "select": {"is_not_empty": True}}
```

### multi_select
```python
{"property": "Tags", "multi_select": {"contains": "Bug"}}
{"property": "Tags", "multi_select": {"does_not_contain": "Bug"}}
{"property": "Tags", "multi_select": {"is_empty": True}}
{"property": "Tags", "multi_select": {"is_not_empty": True}}
```

### status
```python
{"property": "Status", "status": {"equals": "In Progress"}}
{"property": "Status", "status": {"does_not_equal": "Done"}}
{"property": "Status", "status": {"is_empty": True}}
{"property": "Status", "status": {"is_not_empty": True}}
```

### date
```python
{"property": "Due", "date": {"equals": "2024-01-15"}}
{"property": "Due", "date": {"before": "2024-01-15"}}
{"property": "Due", "date": {"after": "2024-01-15"}}
{"property": "Due", "date": {"on_or_before": "2024-01-15"}}
{"property": "Due", "date": {"on_or_after": "2024-01-15"}}
{"property": "Due", "date": {"is_empty": True}}
{"property": "Due", "date": {"is_not_empty": True}}

# Relative dates
{"property": "Due", "date": {"past_week": {}}}
{"property": "Due", "date": {"past_month": {}}}
{"property": "Due", "date": {"past_year": {}}}
{"property": "Due", "date": {"this_week": {}}}
{"property": "Due", "date": {"next_week": {}}}
{"property": "Due", "date": {"next_month": {}}}
{"property": "Due", "date": {"next_year": {}}}
```

### people
```python
{"property": "Assignee", "people": {"contains": "user-uuid"}}
{"property": "Assignee", "people": {"does_not_contain": "user-uuid"}}
{"property": "Assignee", "people": {"is_empty": True}}
{"property": "Assignee", "people": {"is_not_empty": True}}
```

### files
```python
{"property": "Attachments", "files": {"is_empty": True}}
{"property": "Attachments", "files": {"is_not_empty": True}}
```

### url / email / phone_number
```python
{"property": "Website", "url": {"equals": "https://example.com"}}
{"property": "Website", "url": {"contains": "example"}}
{"property": "Website", "url": {"is_empty": True}}
# Same conditions as rich_text
```

### relation
```python
{"property": "Project", "relation": {"contains": "page-uuid"}}
{"property": "Project", "relation": {"does_not_contain": "page-uuid"}}
{"property": "Project", "relation": {"is_empty": True}}
{"property": "Project", "relation": {"is_not_empty": True}}
```

### rollup
```python
# Filter based on rollup result type
# For number rollups:
{"property": "Total", "rollup": {"number": {"greater_than": 100}}}

# For date rollups:
{"property": "Earliest", "rollup": {"date": {"before": "2024-01-15"}}}

# Aggregation-specific:
{"property": "Tasks", "rollup": {"any": {"rich_text": {"contains": "bug"}}}}
{"property": "Tasks", "rollup": {"every": {"checkbox": {"equals": True}}}}
{"property": "Tasks", "rollup": {"none": {"status": {"equals": "Blocked"}}}}
```

### formula
```python
# Filter based on formula result type
{"property": "Formula", "formula": {"string": {"contains": "value"}}}
{"property": "Formula", "formula": {"number": {"greater_than": 10}}}
{"property": "Formula", "formula": {"checkbox": {"equals": True}}}
{"property": "Formula", "formula": {"date": {"after": "2024-01-01"}}}
```

### Timestamp filters
```python
{"timestamp": "created_time", "created_time": {"after": "2024-01-01"}}
{"timestamp": "last_edited_time", "last_edited_time": {"past_week": {}}}
```

---

## Compound Filters

### AND
```python
{
    "and": [
        {"property": "Status", "select": {"equals": "In Progress"}},
        {"property": "Priority", "select": {"equals": "P0"}}
    ]
}
```

### OR
```python
{
    "or": [
        {"property": "Status", "select": {"equals": "Todo"}},
        {"property": "Status", "select": {"equals": "In Progress"}}
    ]
}
```

### Nested
```python
{
    "and": [
        {"property": "Done", "checkbox": {"equals": False}},
        {
            "or": [
                {"property": "Priority", "select": {"equals": "P0"}},
                {"property": "Priority", "select": {"equals": "P1"}}
            ]
        }
    ]
}
```

---

## Sorts

```python
sorts = [
    {"property": "Priority", "direction": "ascending"},
    {"property": "Due Date", "direction": "descending"}
]

# Sort by timestamp
sorts = [
    {"timestamp": "created_time", "direction": "descending"}
]
```

Directions: `ascending`, `descending`

Timestamps: `created_time`, `last_edited_time`

**Note**: First sort takes precedence. Multiple sorts are applied in order.

---

## Complete Examples

### Active High-Priority Tasks
```python
response = notion.databases.query(
    database_id="...",
    filter={
        "and": [
            {"property": "Status", "status": {"does_not_equal": "Done"}},
            {
                "or": [
                    {"property": "Priority", "select": {"equals": "P0"}},
                    {"property": "Priority", "select": {"equals": "P1"}}
                ]
            }
        ]
    },
    sorts=[
        {"property": "Priority", "direction": "ascending"},
        {"property": "Due Date", "direction": "ascending"}
    ]
)
```

### Items Due This Week Assigned to User
```python
response = notion.databases.query(
    database_id="...",
    filter={
        "and": [
            {"property": "Due Date", "date": {"this_week": {}}},
            {"property": "Assignee", "people": {"contains": "user-uuid"}},
            {"property": "Done", "checkbox": {"equals": False}}
        ]
    },
    sorts=[{"property": "Due Date", "direction": "ascending"}]
)
```

### Recently Created Items
```python
response = notion.databases.query(
    database_id="...",
    filter={
        "timestamp": "created_time",
        "created_time": {"past_week": {}}
    },
    sorts=[{"timestamp": "created_time", "direction": "descending"}]
)
```

### Items with Specific Tag
```python
response = notion.databases.query(
    database_id="...",
    filter={
        "property": "Tags",
        "multi_select": {"contains": "Bug"}
    }
)
```

### Overdue Items
```python
from datetime import date

response = notion.databases.query(
    database_id="...",
    filter={
        "and": [
            {"property": "Due Date", "date": {"before": date.today().isoformat()}},
            {"property": "Done", "checkbox": {"equals": False}}
        ]
    }
)
```

### Items Modified Today
```python
response = notion.databases.query(
    database_id="...",
    filter={
        "timestamp": "last_edited_time",
        "last_edited_time": {"equals": date.today().isoformat()}
    },
    sorts=[{"timestamp": "last_edited_time", "direction": "descending"}]
)
```
