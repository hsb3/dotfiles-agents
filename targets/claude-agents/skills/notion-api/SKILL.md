---
name: notion-api
description: Write Python scripts to interact with the Notion API. Use when building automation scripts, migration tools, or integrations that create/read/update Notion databases, pages, and blocks. Covers the notion-client SDK, property schemas, database queries, and block manipulation. NOT for direct Notion interaction - use the Notion MCP connector for that.
---

# Notion API Scripting

Write Python scripts using the `notion-client` SDK to interact with Notion workspaces.

## Quick Start

```python
import os
from notion_client import Client

notion = Client(auth=os.environ["NOTION_TOKEN"])

# Search all accessible content
results = notion.search(query="Project")

# Query a database
pages = notion.databases.query(database_id="abc123...")

# Create a page
notion.pages.create(
    parent={"database_id": "abc123..."},
    properties={
        "Name": {"title": [{"text": {"content": "New Item"}}]},
        "Status": {"select": {"name": "Active"}}
    }
)
```

## Installation

```bash
pip install notion-client
```

## Authentication

1. Create integration at https://www.notion.so/my-integrations
2. Copy the "Internal Integration Token" (starts with `ntn_`)
3. Share target pages/databases with the integration via "..." menu → "Connect to"

## Reference Files

| File | Use When |
|------|----------|
| [endpoints.md](references/endpoints.md) | Need API endpoint reference (databases, pages, blocks, search) |
| [property-types.md](references/property-types.md) | Creating database schemas or setting page properties |
| [filters-sorts.md](references/filters-sorts.md) | Querying databases with filters or sorts |
| [blocks.md](references/blocks.md) | Working with page content (paragraphs, lists, etc.) |

## Common Patterns

### Get Database Schema
```python
db = notion.databases.retrieve(database_id="...")
for name, prop in db["properties"].items():
    print(f"{name}: {prop['type']}")
```

### Create Database
```python
notion.databases.create(
    parent={"page_id": "parent-page-id"},
    title=[{"text": {"content": "My Database"}}],
    properties={
        "Name": {"title": {}},
        "Status": {"select": {"options": [
            {"name": "Todo", "color": "red"},
            {"name": "Done", "color": "green"}
        ]}},
        "Due Date": {"date": {}},
        "Assignee": {"people": {}},
        "Priority": {"number": {}}
    }
)
```

### Paginated Query
```python
def query_all(database_id, **kwargs):
    results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        response = notion.databases.query(
            database_id=database_id,
            start_cursor=next_cursor,
            **kwargs
        )
        results.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response.get("next_cursor")
    
    return results
```

### Update Page Properties
```python
notion.pages.update(
    page_id="...",
    properties={
        "Status": {"select": {"name": "Complete"}},
        "Completed": {"date": {"start": "2024-01-15"}}
    }
)
```

### Add Content to Page
```python
notion.blocks.children.append(
    block_id="page-id",
    children=[
        {"paragraph": {"rich_text": [{"text": {"content": "Hello world"}}]}},
        {"heading_2": {"rich_text": [{"text": {"content": "Section"}}]}},
        {"bulleted_list_item": {"rich_text": [{"text": {"content": "Item 1"}}]}}
    ]
)
```

## API Version Note

The Notion API version `2025-09-03` introduced a split between "databases" and "data sources". For most use cases with `notion-client`, the existing `databases.query()` endpoint still works. See Notion's upgrade guide if you need the newer data source APIs.

## Error Handling

```python
from notion_client import APIErrorCode, APIResponseError

try:
    notion.pages.retrieve(page_id="...")
except APIResponseError as e:
    if e.code == APIErrorCode.ObjectNotFound:
        print("Page not found or not shared with integration")
    else:
        raise
```
