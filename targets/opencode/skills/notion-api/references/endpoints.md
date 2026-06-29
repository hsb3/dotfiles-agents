# Notion API Endpoints Reference

## Table of Contents
- [Databases](#databases)
- [Pages](#pages)
- [Blocks](#blocks)
- [Search](#search)
- [Users](#users)
- [Comments](#comments)

---

## Databases

### Create Database
```python
notion.databases.create(
    parent={"page_id": "..."},  # or {"database_id": "..."} for wiki DBs
    title=[{"text": {"content": "Database Title"}}],
    properties={...}  # See property-types.md
)
```

### Retrieve Database
```python
db = notion.databases.retrieve(database_id="...")
# Returns: id, title, properties (schema), parent, created_time, etc.
```

### Update Database
```python
notion.databases.update(
    database_id="...",
    title=[{"text": {"content": "New Title"}}],
    properties={
        "New Column": {"rich_text": {}},  # Add column
        "Old Column": None  # Remove column
    }
)
```

### Query Database
```python
response = notion.databases.query(
    database_id="...",
    filter={...},      # See filters-sorts.md
    sorts=[...],       # See filters-sorts.md
    page_size=100,     # Max 100
    start_cursor="..." # For pagination
)
# Returns: results[], has_more, next_cursor
```

---

## Pages

### Create Page
```python
# In a database
notion.pages.create(
    parent={"database_id": "..."},
    properties={...}  # See property-types.md for page property values
)

# As child of page (not in database)
notion.pages.create(
    parent={"page_id": "..."},
    properties={"title": {"title": [{"text": {"content": "Page Title"}}]}}
)
```

### Retrieve Page
```python
page = notion.pages.retrieve(page_id="...")
# Returns: id, properties, parent, created_time, last_edited_time, archived, url
```

### Update Page
```python
notion.pages.update(
    page_id="...",
    properties={...},  # Update specific properties
    archived=True      # Optional: archive/unarchive
)
```

### Retrieve Page Property
```python
# For paginated properties (relations, rollups with many items)
prop = notion.pages.properties.retrieve(
    page_id="...",
    property_id="..."  # Get from page["properties"]["PropName"]["id"]
)
```

---

## Blocks

### Retrieve Block
```python
block = notion.blocks.retrieve(block_id="...")
```

### Get Block Children
```python
children = notion.blocks.children.list(
    block_id="...",  # Can be page_id
    page_size=100,
    start_cursor="..."
)
# Returns: results[], has_more, next_cursor
```

### Append Block Children
```python
notion.blocks.children.append(
    block_id="...",  # Parent block or page
    children=[...]   # See blocks.md for block types
)
```

### Update Block
```python
notion.blocks.update(
    block_id="...",
    paragraph={"rich_text": [{"text": {"content": "Updated text"}}]}
)
```

### Delete Block
```python
notion.blocks.delete(block_id="...")
```

---

## Search

```python
results = notion.search(
    query="search term",        # Optional
    filter={"property": "object", "value": "page"},  # or "database"
    sort={"direction": "descending", "timestamp": "last_edited_time"},
    page_size=100,
    start_cursor="..."
)
# Returns: results[], has_more, next_cursor
```

---

## Users

### List Users
```python
users = notion.users.list(page_size=100)
```

### Retrieve User
```python
user = notion.users.retrieve(user_id="...")
```

### Get Bot User (Current Integration)
```python
bot = notion.users.me()
```

---

## Comments

### Create Comment
```python
# On a page
notion.comments.create(
    parent={"page_id": "..."},
    rich_text=[{"text": {"content": "Comment text"}}]
)

# On a discussion thread
notion.comments.create(
    discussion_id="...",
    rich_text=[{"text": {"content": "Reply"}}]
)
```

### List Comments
```python
comments = notion.comments.list(block_id="...")  # page_id works too
```

---

## Response Pagination Pattern

All list endpoints return paginated responses:

```python
def get_all_results(endpoint_method, **kwargs):
    results = []
    has_more = True
    next_cursor = None
    
    while has_more:
        response = endpoint_method(start_cursor=next_cursor, **kwargs)
        results.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response.get("next_cursor")
    
    return results

# Usage
all_pages = get_all_results(notion.databases.query, database_id="...")
all_blocks = get_all_results(notion.blocks.children.list, block_id="...")
```

---

## Rate Limits

- **Average**: 3 requests/second
- **Burst**: Higher temporarily allowed
- On 429 response: Retry after `Retry-After` header seconds

```python
import time
from notion_client import APIResponseError

def rate_limited_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except APIResponseError as e:
        if e.status == 429:
            retry_after = int(e.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            return func(*args, **kwargs)
        raise
```
