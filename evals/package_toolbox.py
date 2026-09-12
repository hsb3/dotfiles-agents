#!/usr/bin/env python3
"""Build the small, source-derived public toolbox deployment context."""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path


WORKFLOW_HEADING = re.compile(r"^(#{2,})\s+Choose a workflow\s*$")
PLUGIN_LINK = re.compile(r"\[([^]]+)\]\(\.\./plugins/([^/]+)/README\.md\)")
UI_SUFFIXES = {".css", ".gif", ".html", ".ico", ".jpeg", ".jpg", ".js", ".json", ".map", ".png", ".svg", ".webp", ".woff", ".woff2"}


def _workflow_rows(workflows):
    lines = workflows.read_text(encoding="utf-8").splitlines()
    start = next((index for index, line in enumerate(lines) if WORKFLOW_HEADING.match(line)), None)
    if start is None:
        raise ValueError("workflows.md has no 'Choose a workflow' table")
    table = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            table.append(line)
        elif table:
            break
    if len(table) < 3:
        raise ValueError("workflow table is missing rows")
    header = [cell.strip() for cell in table[0].strip("|").split("|")]
    if header != ["Stage", "Current marketplace plugin(s)", "Choose them when"]:
        raise ValueError("workflow table header is malformed")
    if not re.fullmatch(r"\|\s*:?-+:?\s*\|\s*:?-+:?\s*\|\s*:?-+:?\s*\|", table[1]):
        raise ValueError("workflow table separator is malformed")
    rows = []
    for line in table[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 3 or not all(cells):
            raise ValueError(f"workflow table row is malformed: {line}")
        links = PLUGIN_LINK.findall(cells[1])
        if not links:
            raise ValueError(f"workflow table has no plugin references: {line}")
        rows.append((cells[0], cells[2], links))
    return rows


def build_catalog(source_root):
    """Return catalog bytes derived solely from the two canonical source files."""
    source_root = Path(source_root)
    manifest_path = source_root / ".claude-plugin" / "marketplace.json"
    workflows_path = source_root / "docs" / "workflows.md"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"missing marketplace manifest: {manifest_path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed marketplace manifest: {error}") from error
    plugins = manifest.get("plugins")
    if not isinstance(plugins, list):
        raise ValueError("marketplace manifest plugins must be a list")
    by_id = {}
    for plugin in plugins:
        if not isinstance(plugin, dict) or not isinstance(plugin.get("name"), str):
            raise ValueError("marketplace manifest contains a plugin without a name")
        plugin_id = plugin["name"]
        if plugin_id in by_id:
            raise ValueError(f"marketplace manifest duplicates plugin: {plugin_id}")
        by_id[plugin_id] = plugin

    workflows = {plugin_id: [] for plugin_id in by_id}
    for stage, guidance, links in _workflow_rows(workflows_path):
        for label, plugin_id in links:
            if label != plugin_id:
                raise ValueError(f"workflow plugin label/path mismatch: {label} != {plugin_id}")
            if plugin_id not in by_id:
                raise ValueError(f"workflow references unknown marketplace plugin: {plugin_id}")
            workflows[plugin_id].append({"stage": stage, "guidance": guidance})

    snapshot = hashlib.sha256(manifest_path.read_bytes() + b"\0" + workflows_path.read_bytes()).hexdigest()
    catalog = {
        "source_snapshot": snapshot,
        "plugins": [
            {
                "id": plugin_id,
                "version": by_id[plugin_id].get("version", ""),
                "description": by_id[plugin_id].get("description", ""),
                "workflows": sorted(workflows[plugin_id], key=lambda row: (row["stage"], row["guidance"])),
            }
            for plugin_id in sorted(by_id)
        ],
    }
    return json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _ui_files(source_ui):
    if not source_ui.is_dir() or not (source_ui / "index.html").is_file():
        raise FileNotFoundError(f"required UI sources are missing: {source_ui}")
    files = []
    for item in sorted(source_ui.rglob("*")):
        if item.is_dir():
            continue
        if not item.is_file() or item.is_symlink() or item.suffix.lower() not in UI_SUFFIXES:
            raise ValueError(f"UI source must be a regular static asset: {item}")
        files.append(item)
    return files


def _copy_ui(files, source_ui, destination):
    for item in files:
        target = destination / item.relative_to(source_ui)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, target)


def build_package(source_root, output):
    """Build an empty, isolated deployment directory at caller-selected *output*."""
    source_root, output = Path(source_root), Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    deploy = source_root / "evals" / "deploy"
    required = [deploy / name for name in ("Dockerfile", "start.sh", "railway.toml")]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing deployment source: " + ", ".join(missing))
    catalog = build_catalog(source_root)
    source_ui = source_root / "evals" / "ui"
    ui_files = _ui_files(source_ui)
    output.mkdir(parents=True)
    for source in required:
        shutil.copyfile(source, output / source.name)
    public = output / "pb_public"
    _copy_ui(ui_files, source_ui, public)
    (public / "toolbox-catalog.json").write_bytes(catalog)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new deployment directory to create")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    build_package(args.source_root, args.output)


if __name__ == "__main__":
    main()
