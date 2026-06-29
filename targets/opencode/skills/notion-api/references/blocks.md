# Notion Blocks Reference

Blocks are the content units within Notion pages.

---

## Table of Contents
- [Block Structure](#block-structure)
- [Text Blocks](#text-blocks)
- [List Blocks](#list-blocks)
- [Media Blocks](#media-blocks)
- [Embed Blocks](#embed-blocks)
- [Layout Blocks](#layout-blocks)
- [Database Blocks](#database-blocks)
- [Reading Blocks](#reading-blocks)
- [Updating Blocks](#updating-blocks)

---

## Block Structure

All blocks share common properties:
```python
{
    "object": "block",
    "id": "block-uuid",
    "parent": {"type": "page_id", "page_id": "..."},
    "type": "paragraph",  # Block type
    "created_time": "2024-01-15T10:00:00.000Z",
    "last_edited_time": "2024-01-15T10:00:00.000Z",
    "has_children": False,
    "archived": False,
    # Type-specific content:
    "paragraph": {"rich_text": [...]}
}
```

---

## Text Blocks

### paragraph
```python
{
    "paragraph": {
        "rich_text": [{"text": {"content": "Paragraph text"}}],
        "color": "default"  # Optional
    }
}
```

### heading_1 / heading_2 / heading_3
```python
{"heading_1": {"rich_text": [{"text": {"content": "Main Heading"}}]}}
{"heading_2": {"rich_text": [{"text": {"content": "Section"}}]}}
{"heading_3": {"rich_text": [{"text": {"content": "Subsection"}}]}}

# With toggle
{"heading_1": {
    "rich_text": [{"text": {"content": "Collapsible"}}],
    "is_toggleable": True
}}
```

### callout
```python
{
    "callout": {
        "rich_text": [{"text": {"content": "Important note"}}],
        "icon": {"emoji": "💡"},  # or {"external": {"url": "..."}}
        "color": "blue_background"
    }
}
```

### quote
```python
{
    "quote": {
        "rich_text": [{"text": {"content": "Quoted text"}}],
        "color": "default"
    }
}
```

### code
```python
{
    "code": {
        "rich_text": [{"text": {"content": "print('Hello')"}}],
        "language": "python",  # See language list below
        "caption": []  # Optional rich_text array
    }
}
```

Languages: `abap`, `arduino`, `bash`, `basic`, `c`, `clojure`, `coffeescript`, `cpp`, `csharp`, `css`, `dart`, `diff`, `docker`, `elixir`, `elm`, `erlang`, `flow`, `fortran`, `fsharp`, `gherkin`, `glsl`, `go`, `graphql`, `groovy`, `haskell`, `html`, `java`, `javascript`, `json`, `julia`, `kotlin`, `latex`, `less`, `lisp`, `livescript`, `lua`, `makefile`, `markdown`, `markup`, `matlab`, `mermaid`, `nix`, `objectivec`, `ocaml`, `pascal`, `perl`, `php`, `plain text`, `powershell`, `prolog`, `protobuf`, `python`, `r`, `reason`, `ruby`, `rust`, `sass`, `scala`, `scheme`, `scss`, `shell`, `sql`, `swift`, `toml`, `typescript`, `vb.net`, `verilog`, `vhdl`, `visual basic`, `webassembly`, `xml`, `yaml`, `java/c/c++/c#`

---

## List Blocks

### bulleted_list_item
```python
{"bulleted_list_item": {"rich_text": [{"text": {"content": "Item 1"}}]}}
```

### numbered_list_item
```python
{"numbered_list_item": {"rich_text": [{"text": {"content": "Step 1"}}]}}
```

### to_do
```python
{
    "to_do": {
        "rich_text": [{"text": {"content": "Task description"}}],
        "checked": False
    }
}
```

### toggle
```python
{
    "toggle": {
        "rich_text": [{"text": {"content": "Click to expand"}}]
        # Children can be added after creation
    }
}
```

**Note**: List items are siblings, not nested in a parent list block. Nesting is done via children.

---

## Media Blocks

### image
```python
# External URL
{
    "image": {
        "type": "external",
        "external": {"url": "https://example.com/image.png"},
        "caption": [{"text": {"content": "Image caption"}}]  # Optional
    }
}

# Notion-hosted (read-only, from uploads)
{
    "image": {
        "type": "file",
        "file": {"url": "...", "expiry_time": "..."}
    }
}
```

### video
```python
{
    "video": {
        "type": "external",
        "external": {"url": "https://youtube.com/watch?v=..."}
    }
}
```

### audio
```python
{
    "audio": {
        "type": "external",
        "external": {"url": "https://example.com/audio.mp3"}
    }
}
```

### file
```python
{
    "file": {
        "type": "external",
        "external": {"url": "https://example.com/doc.pdf"},
        "caption": [],
        "name": "Document.pdf"  # Optional display name
    }
}
```

### pdf
```python
{
    "pdf": {
        "type": "external",
        "external": {"url": "https://example.com/doc.pdf"}
    }
}
```

---

## Embed Blocks

### bookmark
```python
{
    "bookmark": {
        "url": "https://example.com",
        "caption": []
    }
}
```

### embed
```python
{
    "embed": {
        "url": "https://twitter.com/user/status/123"
    }
}
```

### equation (block level)
```python
{
    "equation": {
        "expression": "E = mc^2"
    }
}
```

---

## Layout Blocks

### divider
```python
{"divider": {}}
```

### table_of_contents
```python
{"table_of_contents": {"color": "default"}}
```

### breadcrumb
```python
{"breadcrumb": {}}
```

### column_list and column
```python
# Column list contains columns as children
# Must create via append, then add children to each column

# Step 1: Create column_list with columns
notion.blocks.children.append(
    block_id="page-id",
    children=[{
        "column_list": {
            "children": [
                {"column": {"children": []}},
                {"column": {"children": []}}
            ]
        }
    }]
)

# Step 2: Add content to columns (get column IDs first)
```

---

## Database Blocks

### child_database
```python
{
    "child_database": {
        "title": "Inline Database"
    }
}
# Note: Creates database, properties configured separately
```

### child_page
```python
{
    "child_page": {
        "title": "Subpage Title"
    }
}
```

---

## Reading Blocks

### Get Page Content
```python
def get_page_content(page_id):
    blocks = []
    has_more = True
    next_cursor = None
    
    while has_more:
        response = notion.blocks.children.list(
            block_id=page_id,
            start_cursor=next_cursor,
            page_size=100
        )
        blocks.extend(response["results"])
        has_more = response["has_more"]
        next_cursor = response.get("next_cursor")
    
    return blocks
```

### Get Nested Content
```python
def get_all_blocks(block_id, depth=0):
    """Recursively get all blocks including nested children"""
    blocks = []
    response = notion.blocks.children.list(block_id=block_id)
    
    for block in response["results"]:
        block["_depth"] = depth
        blocks.append(block)
        
        if block.get("has_children"):
            children = get_all_blocks(block["id"], depth + 1)
            blocks.extend(children)
    
    return blocks
```

### Extract Plain Text
```python
def extract_text(blocks):
    """Extract plain text from blocks"""
    text_parts = []
    
    for block in blocks:
        block_type = block["type"]
        content = block.get(block_type, {})
        
        if "rich_text" in content:
            text = "".join(rt["plain_text"] for rt in content["rich_text"])
            text_parts.append(text)
    
    return "\n".join(text_parts)
```

---

## Updating Blocks

### Update Text Content
```python
notion.blocks.update(
    block_id="...",
    paragraph={
        "rich_text": [{"text": {"content": "Updated content"}}]
    }
)
```

### Update To-Do Status
```python
notion.blocks.update(
    block_id="...",
    to_do={
        "rich_text": [{"text": {"content": "Task"}}],
        "checked": True
    }
)
```

### Delete Block
```python
notion.blocks.delete(block_id="...")
```

---

## Complete Example: Create Document

```python
def create_document(page_id, title, sections):
    """
    Create a structured document with heading and content sections.
    
    sections = [
        {"heading": "Introduction", "content": "..."},
        {"heading": "Details", "content": "...", "items": ["a", "b", "c"]},
    ]
    """
    children = []
    
    # Title as H1
    children.append({
        "heading_1": {"rich_text": [{"text": {"content": title}}]}
    })
    
    children.append({"divider": {}})
    
    for section in sections:
        # Section heading
        children.append({
            "heading_2": {"rich_text": [{"text": {"content": section["heading"]}}]}
        })
        
        # Section content
        if section.get("content"):
            children.append({
                "paragraph": {"rich_text": [{"text": {"content": section["content"]}}]}
            })
        
        # Optional bullet list
        if section.get("items"):
            for item in section["items"]:
                children.append({
                    "bulleted_list_item": {"rich_text": [{"text": {"content": item}}]}
                })
    
    # Append all at once (more efficient)
    notion.blocks.children.append(block_id=page_id, children=children)
```

### Create Page with Content
```python
# Create page
page = notion.pages.create(
    parent={"database_id": "..."},
    properties={
        "Name": {"title": [{"text": {"content": "New Doc"}}]}
    }
)

# Add content
notion.blocks.children.append(
    block_id=page["id"],
    children=[
        {"heading_1": {"rich_text": [{"text": {"content": "Overview"}}]}},
        {"paragraph": {"rich_text": [{"text": {"content": "This document..."}}]}},
        {"callout": {
            "rich_text": [{"text": {"content": "Important note"}}],
            "icon": {"emoji": "⚠️"},
            "color": "yellow_background"
        }},
        {"heading_2": {"rich_text": [{"text": {"content": "Steps"}}]}},
        {"numbered_list_item": {"rich_text": [{"text": {"content": "First"}}]}},
        {"numbered_list_item": {"rich_text": [{"text": {"content": "Second"}}]}},
        {"numbered_list_item": {"rich_text": [{"text": {"content": "Third"}}]}}
    ]
)
```
