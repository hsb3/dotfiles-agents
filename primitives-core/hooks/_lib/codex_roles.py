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
MANAGED = "# atelier managed sha256="
HARNESS_BLOCK = re.compile(r"^[ \t]*<!-- harness:[^\n]+ -->\n.*?^[ \t]*<!-- /harness -->\n?",
                           re.MULTILINE | re.DOTALL)


def _role(role):
    if not isinstance(role, str):
        raise ValueError("atelier role must be a string")
    role = role.removeprefix("atelier-")
    if role not in ROLES:
        raise ValueError(f"unknown atelier role: {role!r}")
    return role


def _source(role, plugin_root):
    text = (Path(plugin_root or PACKAGE) / "agents" / f"{_role(role)}.md").read_text()
    if not text.startswith("---\n"):
        raise ValueError(f"role {_role(role)} has no frontmatter")
    frontmatter, body = text[4:].split("\n---\n", 1)
    fields = dict(re.findall(r"^(name|description|tier|effort): (.+)$", frontmatter, re.MULTILINE))
    return fields, body


def role_instructions(role, plugin_root=None):
    """Canonical neutral role + Codex procedures; lifecycle injects this as developer context."""
    _, body = _source(role, plugin_root)
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
    values = {"name": "atelier-" + _role(role), "description": description,
              "model": model, "model_reasoning_effort": fields.get("effort", "medium"),
              "developer_instructions": role_instructions(role, plugin_root)}
    body = "".join(f"{key} = {json.dumps(value, ensure_ascii=False)}\n"
                   for key, value in values.items())
    return MANAGED + hashlib.sha256(body.encode()).hexdigest() + "\n" + body


def setup(project_root, plugin_root=None, check=False):
    """Return missing/stale paths; check is read-only, setup writes only proven-owned files.

    All collisions are checked before writes. An interrupted refresh can leave mixed versions;
    each file remains complete and ownership-checkable, so repeating setup safely finishes it.
    """
    project = Path(project_root).resolve(strict=True)
    directory = project / ".codex/agents"
    for parent in (project / ".codex", directory):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError(f"refusing symlink or non-directory: {parent}")
    names = {"atelier-" + role for role in ROLES}
    for path in directory.glob("*.toml"):
        if path.stem in names:
            continue
        if path.is_file() and tomllib.loads(path.read_text()).get("name") in names:
            raise ValueError(f"atelier role name already declared in user profile: {path}")
    changed = {}
    for role in ROLES:
        path = directory / f"atelier-{role}.toml"
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"refusing non-regular profile: {path}")
        desired = render(role, plugin_root)
        if path.exists():
            current = path.read_text()
            header, _, body = current.partition("\n")
            if not header.startswith(MANAGED):
                raise ValueError(f"refusing unmanaged profile: {path}")
            if header != MANAGED + hashlib.sha256(body.encode()).hexdigest():
                raise ValueError(f"refusing modified managed profile: {path}")
            if current == desired:
                continue
        changed[path] = desired
    if changed and not check:
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
    return list(changed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--check", action="store_true", help="report missing/stale profiles without writing")
    parser.add_argument("--instructions", choices=["atelier-" + r for r in ROLES])
    args = parser.parse_args(argv)
    try:
        if args.instructions:
            print(role_instructions(args.instructions), end="")
            return 0
        changed = setup(args.project, check=args.check)
        for path in changed:
            print(f"{'needs refresh' if args.check else 'wrote'}: {path}")
        if not changed:
            print("atelier Codex profiles are current")
        return int(args.check and bool(changed))
    except (OSError, ValueError, KeyError) as exc:
        print(f"atelier Codex roles: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
