#!/usr/bin/env python3
"""
Memory management for diagrams skill.
- View memory entries
- Add new learnings
- Search for relevant entries
"""

import argparse
import re
from datetime import datetime
from pathlib import Path


MEMORY_FILE = Path(__file__).parent.parent / "memory" / "MEMORY.md"

SECTIONS = [
    "Import Errors",
    "Layout Issues", 
    "Styling Problems",
    "Connection/Flow Issues",
    "Provider-Specific Notes",
    "General Best Practices",
]


def read_memory() -> str:
    """Read the memory file contents."""
    if not MEMORY_FILE.exists():
        return ""
    return MEMORY_FILE.read_text()


def view_memory(section: str = None) -> None:
    """Display memory contents, optionally filtered by section."""
    content = read_memory()
    
    if not content.strip():
        print("Memory file is empty.")
        return
    
    if section:
        # Extract specific section
        pattern = rf"## {re.escape(section)}.*?(?=\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            print(match.group(0))
        else:
            print(f"Section '{section}' not found.")
    else:
        print(content)


def search_memory(query: str) -> None:
    """Search memory for entries matching query."""
    content = read_memory()
    
    if not content:
        print("Memory file is empty.")
        return
    
    # Find all entries (### headers and following content)
    entries = re.findall(r"(### .+?)(?=\n### |\n## |\Z)", content, re.DOTALL)
    
    matches = []
    query_lower = query.lower()
    for entry in entries:
        if query_lower in entry.lower():
            matches.append(entry.strip())
    
    if matches:
        print(f"Found {len(matches)} matching entries:\n")
        for match in matches:
            print(match)
            print("-" * 40)
    else:
        print(f"No entries found matching '{query}'")


def add_entry(section: str, title: str, problem: str, solution: str, example: str = None) -> None:
    """Add a new entry to the memory file."""
    if section not in SECTIONS:
        print(f"Invalid section. Choose from: {', '.join(SECTIONS)}")
        return
    
    content = read_memory()
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Build the entry
    entry = f"\n### {date} - {title}\n"
    entry += f"**Problem**: {problem}\n"
    entry += f"**Solution**: {solution}\n"
    
    if example:
        entry += f"**Example**:\n```python\n{example}\n```\n"
    
    # Find the section and append
    section_header = f"## {section}"
    if section_header in content:
        # Find position after section header (and any existing content)
        pattern = rf"(## {re.escape(section)}.*?)(\n## |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insert_pos = match.end(1)
            new_content = content[:insert_pos] + entry + content[insert_pos:]
            MEMORY_FILE.write_text(new_content)
            print(f"Added entry to '{section}': {title}")
        else:
            print(f"Could not find section: {section}")
    else:
        # Section doesn't exist, append at end
        content += f"\n{section_header}\n{entry}"
        MEMORY_FILE.write_text(content)
        print(f"Created section '{section}' and added entry: {title}")


def list_sections() -> None:
    """List available sections."""
    print("Available sections:")
    for section in SECTIONS:
        print(f"  - {section}")


def main():
    parser = argparse.ArgumentParser(description="Manage diagram skill memory")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # View command
    view_parser = subparsers.add_parser("view", help="View memory contents")
    view_parser.add_argument("--section", "-s", help="Filter by section name")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search memory")
    search_parser.add_argument("query", help="Search query")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add new entry")
    add_parser.add_argument("--section", "-s", required=True, help="Section name")
    add_parser.add_argument("--title", "-t", required=True, help="Entry title")
    add_parser.add_argument("--problem", "-p", required=True, help="Problem description")
    add_parser.add_argument("--solution", "-o", required=True, help="Solution description")
    add_parser.add_argument("--example", "-e", help="Code example")
    
    # Sections command
    subparsers.add_parser("sections", help="List available sections")
    
    args = parser.parse_args()
    
    if args.command == "view":
        view_memory(args.section)
    elif args.command == "search":
        search_memory(args.query)
    elif args.command == "add":
        add_entry(args.section, args.title, args.problem, args.solution, args.example)
    elif args.command == "sections":
        list_sections()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
