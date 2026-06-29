# Notion Property Types Reference

Two contexts for property definitions:
1. **Database Schema** - Defining columns when creating/updating databases
2. **Page Property Values** - Setting values when creating/updating pages

---

## Table of Contents
- [Database Schema Properties](#database-schema-properties)
- [Page Property Values](#page-property-values)
- [Rich Text Object](#rich-text-object)

---

## Database Schema Properties

Used in `notion.databases.create()` and `notion.databases.update()`.

### title (Required - exactly one per database)
```python
"Name": {"title": {}}
```

### rich_text
```python
"Description": {"rich_text": {}}
```

### number
```python
"Price": {"number": {}}
# With format:
"Price": {"number": {"format": "dollar"}}
# Formats: number, number_with_commas, percent, dollar, canadian_dollar, 
#          euro, pound, yen, ruble, rupee, won, yuan, real, lira, etc.
```

### select
```python
"Status": {
    "select": {
        "options": [
            {"name": "Todo", "color": "red"},
            {"name": "In Progress", "color": "yellow"},
            {"name": "Done", "color": "green"}
        ]
    }
}
# Colors: default, gray, brown, orange, yellow, green, blue, purple, pink, red
```

### multi_select
```python
"Tags": {
    "multi_select": {
        "options": [
            {"name": "Frontend", "color": "blue"},
            {"name": "Backend", "color": "green"},
            {"name": "Bug", "color": "red"}
        ]
    }
}
```

### status
```python
# NOTE: Cannot be created via API - only available if already exists in DB
# Can read but not create status properties
```

### date
```python
"Due Date": {"date": {}}
```

### people
```python
"Assignee": {"people": {}}
```

### files
```python
"Attachments": {"files": {}}
```

### checkbox
```python
"Completed": {"checkbox": {}}
```

### url
```python
"Website": {"url": {}}
```

### email
```python
"Contact Email": {"email": {}}
```

### phone_number
```python
"Phone": {"phone_number": {}}
```

### relation
```python
# One-way relation
"Project": {
    "relation": {
        "database_id": "target-database-id",
        "single_property": {}
    }
}

# Two-way relation (creates property in both databases)
"Tasks": {
    "relation": {
        "database_id": "target-database-id",
        "dual_property": {
            "synced_property_name": "Parent Project"  # Name in target DB
        }
    }
}
```

### rollup
```python
"Total Hours": {
    "rollup": {
        "relation_property_name": "Tasks",      # Name of relation property
        "rollup_property_name": "Hours",        # Property in related DB
        "function": "sum"
    }
}
# Functions: count, count_values, empty, not_empty, unique, show_unique,
#            percent_empty, percent_not_empty, sum, average, median,
#            min, max, range, earliest_date, latest_date, date_range,
#            checked, unchecked, percent_checked, percent_unchecked,
#            show_original
```

### formula
```python
"Calculated": {
    "formula": {
        "expression": "prop(\"Price\") * prop(\"Quantity\")"
    }
}
```

### created_time / created_by / last_edited_time / last_edited_by
```python
"Created": {"created_time": {}}
"Created By": {"created_by": {}}
"Last Edited": {"last_edited_time": {}}
"Last Edited By": {"last_edited_by": {}}
```

---

## Page Property Values

Used in `notion.pages.create()` and `notion.pages.update()`.

### title
```python
"Name": {
    "title": [
        {"text": {"content": "Page Title"}}
    ]
}
```

### rich_text
```python
"Description": {
    "rich_text": [
        {"text": {"content": "Plain text"}},
        {"text": {"content": "bold"}, "annotations": {"bold": True}},
        {"text": {"content": "link", "link": {"url": "https://..."}}}
    ]
}
```

### number
```python
"Price": {"number": 99.99}
```

### select
```python
"Status": {"select": {"name": "In Progress"}}
# New options are created automatically if they don't exist
```

### multi_select
```python
"Tags": {
    "multi_select": [
        {"name": "Frontend"},
        {"name": "Bug"}
    ]
}
```

### status
```python
"Status": {"status": {"name": "In Progress"}}
# Only works with existing status options
```

### date
```python
# Date only
"Due Date": {"date": {"start": "2024-01-15"}}

# Date with time
"Meeting": {"date": {"start": "2024-01-15T09:00:00"}}

# Date range
"Sprint": {"date": {"start": "2024-01-15", "end": "2024-01-29"}}

# With timezone
"Event": {"date": {"start": "2024-01-15T09:00:00", "time_zone": "America/New_York"}}
```

### people
```python
"Assignee": {
    "people": [
        {"id": "user-uuid-here"}
    ]
}
```

### files
```python
# External URL
"Attachments": {
    "files": [
        {"name": "Document", "type": "external", "external": {"url": "https://..."}}
    ]
}
# Note: Uploading files requires separate File Upload API
```

### checkbox
```python
"Completed": {"checkbox": True}
```

### url
```python
"Website": {"url": "https://example.com"}
```

### email
```python
"Contact": {"email": "user@example.com"}
```

### phone_number
```python
"Phone": {"phone_number": "+1-555-1234"}
```

### relation
```python
"Project": {
    "relation": [
        {"id": "related-page-uuid-1"},
        {"id": "related-page-uuid-2"}
    ]
}
```

### Read-only properties (cannot be set)
- `formula` - Calculated automatically
- `rollup` - Calculated automatically  
- `created_time` - Set automatically
- `created_by` - Set automatically
- `last_edited_time` - Set automatically
- `last_edited_by` - Set automatically
- `unique_id` - Set automatically

---

## Rich Text Object

Used in title, rich_text properties, and block content.

### Basic Structure
```python
{
    "type": "text",  # or "mention", "equation"
    "text": {
        "content": "The actual text",
        "link": {"url": "https://..."} | None
    },
    "annotations": {
        "bold": False,
        "italic": False,
        "strikethrough": False,
        "underline": False,
        "code": False,
        "color": "default"  # See colors below
    },
    "plain_text": "The actual text",  # Read-only
    "href": None  # Read-only
}
```

### Colors
`default`, `gray`, `brown`, `orange`, `yellow`, `green`, `blue`, `purple`, `pink`, `red`

Background variants: `gray_background`, `brown_background`, etc.

### Mentions
```python
# User mention
{"type": "mention", "mention": {"type": "user", "user": {"id": "user-uuid"}}}

# Page mention
{"type": "mention", "mention": {"type": "page", "page": {"id": "page-uuid"}}}

# Database mention
{"type": "mention", "mention": {"type": "database", "database": {"id": "db-uuid"}}}

# Date mention
{"type": "mention", "mention": {"type": "date", "date": {"start": "2024-01-15"}}}
```

### Equation
```python
{"type": "equation", "equation": {"expression": "E = mc^2"}}
```

---

## Complete Database Creation Example

```python
notion.databases.create(
    parent={"page_id": "parent-page-uuid"},
    title=[{"text": {"content": "Project Tracker"}}],
    properties={
        "Name": {"title": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "Backlog", "color": "gray"},
                    {"name": "In Progress", "color": "blue"},
                    {"name": "Done", "color": "green"}
                ]
            }
        },
        "Priority": {
            "select": {
                "options": [
                    {"name": "P0", "color": "red"},
                    {"name": "P1", "color": "orange"},
                    {"name": "P2", "color": "yellow"}
                ]
            }
        },
        "Assignee": {"people": {}},
        "Due Date": {"date": {}},
        "Estimate": {"number": {"format": "number"}},
        "Tags": {
            "multi_select": {
                "options": [
                    {"name": "Bug", "color": "red"},
                    {"name": "Feature", "color": "green"},
                    {"name": "Tech Debt", "color": "purple"}
                ]
            }
        },
        "Description": {"rich_text": {}},
        "GitHub URL": {"url": {}},
        "Completed": {"checkbox": {}}
    }
)
```

## Complete Page Creation Example

```python
notion.pages.create(
    parent={"database_id": "database-uuid"},
    properties={
        "Name": {"title": [{"text": {"content": "Implement Login"}}]},
        "Status": {"select": {"name": "In Progress"}},
        "Priority": {"select": {"name": "P1"}},
        "Assignee": {"people": [{"id": "user-uuid"}]},
        "Due Date": {"date": {"start": "2024-02-01"}},
        "Estimate": {"number": 5},
        "Tags": {"multi_select": [{"name": "Feature"}]},
        "Description": {"rich_text": [{"text": {"content": "Add OAuth2 login flow"}}]},
        "GitHub URL": {"url": "https://github.com/org/repo/issues/123"},
        "Completed": {"checkbox": False}
    }
)
```
