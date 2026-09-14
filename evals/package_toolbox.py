#!/usr/bin/env python3
"""Build the small, source-derived public toolbox deployment context."""

import argparse
import hashlib
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


WORKFLOW_HEADING = re.compile(r"^(#{2,})\s+Choose a workflow\s*$")
PLUGIN_LINK = re.compile(r"\[([^]]+)\]\(\.\./plugins/([^/]+)/README\.md\)")
UNSAFE_UI_PARTS = {"node_modules", "private", "src"}
UI_BUILD_PATH = Path("evals/ui/dist")


def _input_file(source_root, path):
    source_root, path = Path(source_root), Path(path)
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        raise ValueError(f"package input escapes source root: {path}") from None
    current = source_root
    if current.is_symlink():
        raise ValueError(f"package input ancestor is a symlink: {current}")
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"package input is a symlink: {current}")
    if not path.is_file():
        raise FileNotFoundError(f"required package input is missing: {path}")
    return path


def _unsafe_ui_path(relative):
    return (set(relative.parts) & UNSAFE_UI_PARTS or any(part.startswith("private") for part in relative.parts)
            or relative.name.startswith(".env") or relative.suffix == ".map")


def _source_root(source_root):
    source_root = Path(source_root)
    if ".." in source_root.parts:
        raise ValueError(f"source root traversal is not allowed: {source_root}")
    if source_root.is_symlink():
        raise ValueError(f"source root is a symlink: {source_root}")
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"source root is missing: {source_root}")
    return source_root


def _ui_build_path(source_root, source_root_input, ui_build):
    if ui_build is None:
        raise ValueError("a ui build directory is required")
    ui_build = Path(ui_build)
    if ".." in ui_build.parts:
        raise ValueError(f"ui build traversal is not allowed: {ui_build}")
    expected = Path(source_root_input).absolute() / UI_BUILD_PATH
    candidates = [ui_build.absolute()] if ui_build.is_absolute() else [
        Path(source_root_input).absolute() / ui_build, ui_build.absolute(),
    ]
    if expected not in candidates:
        raise ValueError(f"ui build must be the canonical source build: {expected}")
    return source_root / UI_BUILD_PATH


class _AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.modules = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower() == "module" and attrs.get("src"):
            self.modules.append(attrs["src"])
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower().split() and attrs.get("href"):
            self.stylesheets.append(attrs["href"])


def _validate_asset_references(index, ui_files, ui_build):
    parser = _AssetReferences()
    parser.feed(index.read_text(encoding="utf-8"))
    if not parser.modules:
        raise ValueError("ui build index has no module entry")
    available = {path.relative_to(ui_build).as_posix() for path in ui_files}
    for reference in parser.modules + parser.stylesheets:
        parsed = urlsplit(reference)
        relative = Path(unquote(parsed.path.lstrip("/")))
        if (reference.startswith("//") or parsed.scheme or parsed.netloc or not parsed.path or ".." in relative.parts
                or relative.is_absolute() or _unsafe_ui_path(relative)
                or relative.as_posix() not in available):
            raise ValueError(f"ui build index has unsafe or missing reference: {reference}")


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


def _workflow_id(stage):
    workflow_id = re.sub(r"[^a-z0-9]+", "-", stage.lower()).strip("-")
    if not workflow_id:
        raise ValueError(f"workflow stage has no stable id: {stage}")
    return workflow_id


def build_catalog(source_root):
    """Return catalog bytes derived solely from the two canonical source files."""
    source_root = Path(source_root)
    manifest_path = source_root / ".claude-plugin" / "marketplace.json"
    workflows_path = source_root / "docs" / "workflows.md"
    _input_file(source_root, manifest_path)
    _input_file(source_root, workflows_path)
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

    plugin_workflows = {plugin_id: set() for plugin_id in by_id}
    workflows = {}
    for stage, guidance, links in _workflow_rows(workflows_path):
        workflow_id = _workflow_id(stage)
        workflow = workflows.setdefault(workflow_id, {
            "id": workflow_id, "name": stage, "guidance": guidance, "plugins": set(),
        })
        if workflow["name"] != stage or workflow["guidance"] != guidance:
            raise ValueError(f"workflow stage has conflicting rows: {stage}")
        for label, plugin_id in links:
            if label != plugin_id:
                raise ValueError(f"workflow plugin label/path mismatch: {label} != {plugin_id}")
            if plugin_id not in by_id:
                raise ValueError(f"workflow references unknown marketplace plugin: {plugin_id}")
            workflow["plugins"].add(plugin_id)
            plugin_workflows[plugin_id].add(workflow_id)

    snapshot = hashlib.sha256(manifest_path.read_bytes() + b"\0" + workflows_path.read_bytes()).hexdigest()
    catalog = {
        "source_snapshot": snapshot,
        "plugins": [
            {
                "id": plugin_id,
                "name": plugin_id,
                "version": by_id[plugin_id].get("version", ""),
                "description": by_id[plugin_id].get("description", ""),
                "workflows": sorted(plugin_workflows[plugin_id]),
            }
            for plugin_id in sorted(by_id)
        ],
        "workflows": [
            {**workflow, "plugins": sorted(workflow["plugins"])}
            for _, workflow in sorted(workflows.items())
        ],
    }
    return json.dumps(catalog, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def _ui_files(source_root, source_root_input, ui_build):
    ui_build = _ui_build_path(source_root, source_root_input, ui_build)
    ui_relative = UI_BUILD_PATH
    index = _input_file(source_root, ui_build / "index.html")
    if not ui_build.is_dir() or ui_build.is_symlink():
        raise ValueError(f"ui build is not a regular directory: {ui_build}")
    files = []
    for path in sorted(ui_build.rglob("*")):
        if path.is_dir():
            if path.is_symlink():
                raise ValueError(f"ui build input is a symlink: {path}")
            continue
        relative = path.relative_to(ui_build)
        if path.is_symlink():
            raise ValueError(f"ui build input is a symlink: {path}")
        if not path.is_file():
            raise ValueError(f"ui build input is not a regular file: {path}")
        if _unsafe_ui_path(relative):
            raise ValueError(f"unsafe ui build input: {relative}")
        _input_file(source_root, path)
        files.append(path)
    if not any(path.relative_to(ui_build).parts[0] == "assets" for path in files):
        raise ValueError("ui build has no assets")
    _validate_asset_references(index, files, ui_build)
    return ui_relative, files


def _snapshot_files(files, root):
    digest = hashlib.sha256()
    names = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        names.append(relative)
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return names, digest.hexdigest()


def _ui_source_files(source_root):
    source_ui = Path(source_root) / "evals" / "ui"
    if not source_ui.is_dir() or source_ui.is_symlink():
        raise ValueError(f"ui source is not a regular directory: {source_ui}")
    files = []
    for path in sorted(source_ui.rglob("*")):
        relative = path.relative_to(source_ui)
        if (relative.parts[0] in {"build", "dist", "node_modules"}
                or any(part.startswith("private") for part in relative.parts)
                or relative.name.startswith(".env") or relative.suffix == ".map"):
            continue
        if path.is_dir():
            if path.is_symlink():
                raise ValueError(f"ui source input is a symlink: {path}")
            continue
        if path.is_symlink():
            raise ValueError(f"ui source input is a symlink: {path}")
        if not path.is_file():
            raise ValueError(f"ui source input is not a regular file: {path}")
        _input_file(source_root, path)
        files.append(path)
    return files


def _ui_receipt(source_snapshot, ui_relative, ui_files, ui_build, ui_source_files, ui_source):
    ui_names, ui_snapshot = _snapshot_files(ui_files, ui_build)
    source_names, source_ui_snapshot = _snapshot_files(ui_source_files, ui_source)
    return json.dumps({
        "source_snapshot": source_snapshot,
        "ui_build": ui_relative.as_posix(),
        "ui_files": ui_names,
        "ui_snapshot": ui_snapshot,
        "ui_source_files": source_names,
        "ui_source_snapshot": source_ui_snapshot,
    }, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def build_package(source_root, output, ui_build=None):
    """Build an empty, isolated deployment directory at caller-selected *output*."""
    source_root_input = Path(source_root)
    source_root, output = _source_root(source_root_input), Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    try:
        output.resolve().relative_to(source_root.resolve())
    except ValueError:
        pass
    else:
        raise ValueError(f"output must be outside the source root: {output}")
    deploy = source_root / "evals" / "deploy"
    hook = deploy / "pb_hooks" / "toolbox_catalog.pb.js"
    required = [deploy / name for name in ("Dockerfile", "start.sh", "railway.toml")] + [hook]
    required = [_input_file(source_root, path) for path in required]
    catalog = build_catalog(source_root)
    ui_relative, ui_files = _ui_files(source_root, source_root_input, ui_build)
    ui_source = source_root / "evals" / "ui"
    receipt = _ui_receipt(
        json.loads(catalog)["source_snapshot"], ui_relative, ui_files, source_root / UI_BUILD_PATH,
        _ui_source_files(source_root), ui_source,
    )
    output.mkdir(parents=True)
    for source in required[:3]:
        shutil.copyfile(source, output / source.name)
    hook_target = output / "pb_hooks" / hook.name
    hook_target.parent.mkdir()
    shutil.copyfile(hook, hook_target)
    catalog_target = hook_target.parent / "toolbox-catalog.json"
    catalog_target.write_bytes(catalog)
    (hook_target.parent / "toolbox-package.json").write_bytes(receipt)
    public = output / "pb_public"
    for source in ui_files:
        target = public / source.relative_to(source_root / UI_BUILD_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new deployment directory to create")
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--ui-build", type=Path, required=True, help="Vite build directory inside source root")
    args = parser.parse_args(argv)
    build_package(args.source_root, args.output, args.ui_build)


if __name__ == "__main__":
    main()
