#!/usr/bin/env python3
"""Render canonical atelier roles into ownership-checked project Codex profiles."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib

import model_tiers

ROLES = ("builder", "code-reviewer", "manager", "reviewer", "scout")
PACKAGE = Path(__file__).resolve().parents[2]
HARNESS_BLOCK = re.compile(r"^[ \t]*<!-- harness:[^\n]+ -->\n.*?^[ \t]*<!-- /harness -->\n?",
                           re.MULTILINE | re.DOTALL)


def package_id(plugin_root=None):
    if plugin_root is None:
        return "atelier"
    for relative in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "plugin.json"):
        path = Path(plugin_root) / relative
        if path.is_file():
            data = json.loads(path.read_text())
            name = data.get("name") if isinstance(data, dict) else None
            if isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9-]*", name):
                return name
            raise ValueError(f"invalid package identity: {path}")
    raise ValueError(f"package manifest missing: {plugin_root}")


def roles(plugin_root=None):
    if plugin_root is None:
        return ROLES
    package_id(plugin_root)
    names = tuple(sorted(path.stem for path in (Path(plugin_root) / "agents").glob("*.md")
                         if path.is_file()))
    if not names or any(not re.fullmatch(r"[a-z][a-z0-9-]*", name) for name in names):
        raise ValueError("package has no valid agent assembly")
    return names


def role_names(plugin_root=None):
    return tuple(package_id(plugin_root) + "-" + role for role in roles(plugin_root))


def _role(role, plugin_root=None):
    if not isinstance(role, str):
        raise ValueError("role must be a string")
    names = roles(plugin_root)
    if role not in names:
        role = role.removeprefix(package_id(plugin_root) + "-")
    if role not in names:
        raise ValueError(f"unknown package role: {role!r}")
    return role


def _managed(plugin_root=None):
    return "# " + package_id(plugin_root) + " managed sha256="


def _source(role, plugin_root):
    text = (Path(plugin_root or PACKAGE) / "agents" / f"{_role(role, plugin_root)}.md").read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"role {_role(role, plugin_root)} has no frontmatter")
    frontmatter, body = text[4:].split("\n---\n", 1)
    fields = dict(re.findall(r"^(name|description|tier|effort|tools): (.+)$", frontmatter, re.MULTILINE))
    return fields, body


def role_tools(role, plugin_root=None):
    fields, _ = _source(role, plugin_root)
    return frozenset(tool.strip() for tool in fields['tools'].split(','))


def role_instructions(role, plugin_root=None):
    """Canonical neutral role + Codex procedures; lifecycle injects this as developer context."""
    _, body = _source(role, plugin_root)
    package = Path(plugin_root or PACKAGE).resolve()
    if package_id(plugin_root) != "atelier":
        location = (f"Package: {package}. Companion skills live beneath skills/; "
                    "companion agent bodies live beneath agents/. Read those files from "
                    "this package. Native registration and instructions do not remove tools; "
                    "follow the canonical role authority.")
        return HARNESS_BLOCK.sub("", body).strip() + "\n\n" + location + "\n"
    reference = (Path(plugin_root or PACKAGE) /
                 "skills/delegation/references/dispatch-knobs.md").read_text()
    start = reference.index("## Codex distribution\n")
    procedures = reference[start:reference.index("<!-- /harness -->", start)].strip()
    package = Path(plugin_root or PACKAGE).resolve()
    location = (f"Atelier package: {package}. Resolve companion skills beneath its skills/ directory; "
                "bare delegation reference filenames (including waiting.md) live in "
                "skills/delegation/references/. Read them from this package, not the consumer tree.")
    return HARNESS_BLOCK.sub("", body).strip() + "\n\n" + location + "\n\n" + procedures + "\n"


def render(role, plugin_root=None):
    """One TOML profile; the checksum detects consumer edits before refresh."""
    fields, _ = _source(role, plugin_root)
    catalog = model_tiers.load(str(Path(plugin_root or PACKAGE) / "hooks/_lib/model_catalog.json"))
    model = model_tiers.model_for(catalog, fields["tier"], "openai")
    if not model:
        raise ValueError(f"no OpenAI model for tier {fields['tier']!r}")
    description = fields["description"].strip('"')
    # Claude-specific tier hints are instructions, not part of the portable role description.
    description = description.split(" Defaults to", 1)[0]
    values = {"name": package_id(plugin_root) + "-" + _role(role, plugin_root), "description": description,
              "model": model, "model_reasoning_effort": fields.get("effort", "medium"),
              "developer_instructions": role_instructions(role, plugin_root)}
    body = "".join(f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
                   for key, value in values.items())
    return _managed(plugin_root) + hashlib.sha256(body.encode()).hexdigest() + "\n" + body


def _directory(root, global_profiles=False):
    return Path(root).resolve() / ("agents" if global_profiles else ".codex/agents")


def _changes(directory, plugin_root):
    names = set(role_names(plugin_root))
    managed = _managed(plugin_root)
    for path in directory.glob("*.toml"):
        if path.stem in names:
            continue
        if path.is_file() and tomllib.loads(path.read_text()).get("name") in names:
            raise ValueError(f"atelier role name already declared in user profile: {path}")
    changed = {}
    for role in roles(plugin_root):
        path = directory / f"{package_id(plugin_root)}-{role}.toml"
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"refusing non-regular profile: {path}")
        desired = render(role, plugin_root)
        if path.exists():
            current = path.read_text()
            header, _, body = current.partition("\n")
            if not header.startswith(managed):
                raise ValueError(f"refusing unmanaged profile: {path}")
            if header != managed + hashlib.sha256(body.encode()).hexdigest():
                raise ValueError(f"refusing modified managed profile: {path}")
            if current == desired:
                continue
        changed[path] = desired
    return changed


def _write(directory, changed):
    if not changed:
        return
    directory.mkdir(parents=True, exist_ok=True)
    for path, content in changed.items():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                             prefix=".atelier-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def codex_home():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def setup(project_root, plugin_root=None, check=False, refresh_global=False, global_profiles=False):
    """Return missing/stale paths; check is read-only, setup writes only proven-owned files.

    All collisions are checked before writes. An interrupted refresh can leave mixed versions;
    each file remains complete and ownership-checkable, so repeating setup safely finishes it.
    """
    project = Path(project_root).resolve(strict=True)
    directory = _directory(project, global_profiles)
    parents = (directory.parent, directory)
    for parent in parents:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f"refusing symlink or non-directory: {parent}")
    if global_profiles:
        changed = _changes(directory, plugin_root)
        if changed and not check:
            _write(directory, changed)
        return list(changed)

    local = _changes(directory, plugin_root)
    local_paths = [directory / f"{package_id(plugin_root)}-{role}.toml" for role in roles(plugin_root)]
    if any(path.exists() for path in local_paths):
        if local and not check:
            _write(directory, local)
        return list(local)

    global_directory = _directory(codex_home(), True)
    for parent in (global_directory.parent, global_directory):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f"refusing symlink or non-directory: {parent}")
    global_paths = [global_directory / path.name for path in local_paths]
    if all(path.exists() for path in global_paths):
        try:
            global_changed = _changes(global_directory, plugin_root)
        except ValueError as exc:
            raise ValueError("stale global Codex profiles: " + str(exc)) from exc
        if global_changed:
            if check:
                return list(global_changed)
            if not refresh_global:
                raise ValueError("stale global Codex profiles; rerun with --refresh-global")
            _write(global_directory, global_changed)
            return list(global_changed)
        return []
    if local and not check:
        _write(directory, local)
    return list(local)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--check", action="store_true", help="report missing/stale profiles without writing")
    parser.add_argument("--refresh-global", action="store_true", help="refresh stale managed global profiles")
    parser.add_argument("--plugin-root", type=Path)
    parser.add_argument("--instructions")
    args = parser.parse_args(argv)
    try:
        if args.instructions:
            print(role_instructions(args.instructions, args.plugin_root), end="")
            return 0
        changed = setup(args.project, args.plugin_root, check=args.check,
                        refresh_global=args.refresh_global)
        for path in changed:
            print(f"{'needs refresh' if args.check else 'wrote'}: {path}")
        if not changed:
            print(package_id(args.plugin_root) + " Codex profiles are current")
        return int(args.check and bool(changed))
    except (OSError, ValueError, KeyError) as exc:
        print(f"atelier Codex roles: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
