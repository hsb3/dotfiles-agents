#!/usr/bin/env python3
"""
Memory management for diagrams skill.
- View memory entries
- Add new learnings
- Search for relevant entries
"""

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path


MEMORY_FILE = None


def resolve_memory_file(project_root=None) -> Path:
    """Detect project memory, with a project-local memory-path override."""
    if project_root is None:
        try:
            result = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                                    capture_output=True, text=True, check=True)
            project_root = result.stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            project_root = Path.cwd()
    root = Path(project_root).resolve()
    default = (root / ".claude/memory/diagrams.md" if (root / ".claude/memory").is_dir()
               else root / ".claude/diagrams-memory.md")
    try:
        text = (root / ".claude/diagrams.local.md").read_text()
    except OSError:
        text = ""
    frontmatter = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if frontmatter:
        match = re.search(r'''(?m)^memory-path:[ \t]*(?:"([^"\n]+)"|'([^'\n]+)'|([^#'"\n]+))[ \t]*(?:#.*)?$''',
                          frontmatter[1])
        value = next((v.strip() for v in match.groups() if v is not None), "") if match else ""
        if value and value[0] not in "[{>|":
            candidate = (root / value).resolve()
            if candidate.is_relative_to(root) and not candidate.is_dir():
                return candidate
    if not default.resolve().is_relative_to(root):
        raise ValueError("project memory directory resolves outside the project")
    return default


def memory_file() -> Path:
    return MEMORY_FILE if MEMORY_FILE is not None else resolve_memory_file()

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
    path = memory_file()
    if not path.exists():
        return ""
    return path.read_text()


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
    path = memory_file()
    path.parent.mkdir(parents=True, exist_ok=True)
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
            path.write_text(new_content)
            print(f"Added entry to '{section}': {title}")
        else:
            print(f"Could not find section: {section}")
    else:
        # Section doesn't exist, append at end
        content += f"\n{section_header}\n{entry}"
        path.write_text(content)
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
    subparsers.add_parser("path", help="Print the consumer project's learned-memory path")
    
    args = parser.parse_args()
    
    if args.command == "view":
        view_memory(args.section)
    elif args.command == "search":
        search_memory(args.query)
    elif args.command == "add":
        add_entry(args.section, args.title, args.problem, args.solution, args.example)
    elif args.command == "sections":
        list_sections()
    elif args.command == "path":
        print(memory_file())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
