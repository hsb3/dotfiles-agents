#!/usr/bin/env python3
"""Scaffold a conformant primitives-core/<type>/<id>/ body plus its roster row.

Stdlib-only, deterministic. Fails loudly on a duplicate id rather than overwriting.
Usage:
    python3 scaffold.py skill <id> [--description TEXT]
    python3 scaffold.py agent <id> [--description TEXT]
"""

import argparse
import os
import re
import sys

# this file lives 4 levels under the repo root: .claude/skills/author-primitive/scripts/
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
ROSTER = os.path.join(REPO, "primitives-core.yaml")
SOLO_SKILLS_LINK_DIR = os.path.join(REPO, "plugins", "solo-skills", "skills")
ID_RX = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

DEFAULT_DESCRIPTION = "TODO — describe what this does and when to use it."

SKILL_MD = """---
name: {id}
description: >-
  {description}
---

# {title}

TODO — write the skill body: what it does, the steps it drives, and what it hands back.
"""

SKILL_README = """# {id}

TODO — one paragraph: what it does and the outcome it buys.

## When it triggers

TODO — the asks or events that invoke it, in user phrasing.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Shipping it in another plugin too is a separate, hand-authored step (CONTRIBUTING.md:
"Shipping a primitive in another plugin = one more symlink in that assembly + nothing
else") — add `skills/{id}` to the chosen `plugins/<id>/` and add its
`claude plugin install <id>@dotfiles-agents` line here.
"""

AGENT_MD = """---
name: {id}
description: >-
  {description}
---

You are {id}: TODO — one line on the role.

TODO — write the agent body.
"""

ROSTER_SKILL_ENTRY = """  - id: {id}
    type: skill
    source: primitives-core/skills/{id}
    origin: authored
    disposition: untriaged
    targets: [claude-code]
"""

ROSTER_AGENT_ENTRY = """  - id: {id}
    type: agent
    source: primitives-core/agents/{id}.md
    origin: authored
    disposition: untriaged
    targets: [claude-code]
"""


def _fail(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _check_id(id_):
    if not ID_RX.match(id_):
        _fail(f"{id_!r} is not kebab-case (^[a-z][a-z0-9]*(-[a-z0-9]+)*$)")
    with open(ROSTER, encoding="utf-8") as fh:
        if re.search(rf"^  - id: {re.escape(id_)}\s*$", fh.read(), re.M):
            _fail(f"roster already has an entry for id {id_!r}")


def _append_roster(entry_text):
    with open(ROSTER, encoding="utf-8") as fh:
        text = fh.read()
    if not text.endswith("\n"):
        text += "\n"
    with open(ROSTER, "w", encoding="utf-8") as fh:
        fh.write(text + entry_text)


def scaffold_skill(id_, description):
    _check_id(id_)
    d = os.path.join(REPO, "primitives-core", "skills", id_)
    if os.path.exists(d):
        _fail(f"{d} already exists on disk")
    os.makedirs(d)
    title = id_.replace("-", " ").capitalize()
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(SKILL_MD.format(id=id_, description=description, title=title))
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(SKILL_README.format(id=id_))
    _append_roster(ROSTER_SKILL_ENTRY.format(id=id_))

    # A freshly scaffolded skill is dependency-free by construction, so solo-skills is its
    # derived home (scripts/check_solo_skills.py: membership is derived, not curatorial).
    link = os.path.join(SOLO_SKILLS_LINK_DIR, id_)
    if os.path.lexists(link):
        _fail(f"{link} already exists")
    os.symlink(os.path.join("..", "..", "..", "primitives-core", "skills", id_), link)

    print(f"scaffolded primitives-core/skills/{id_}/ (SKILL.md, README.md) + roster row")
    print(f"linked plugins/solo-skills/skills/{id_} -> primitives-core/skills/{id_}")
    print(
        "shipping this for real also needs a plugins/solo-skills version bump "
        "(scripts/check_version_bump.py, CI-only, not in make ci) — a semantic call for a "
        "human to make at ship time, not this script"
    )


def scaffold_agent(id_, description):
    _check_id(id_)
    f = os.path.join(REPO, "primitives-core", "agents", f"{id_}.md")
    if os.path.exists(f):
        _fail(f"{f} already exists on disk")
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(AGENT_MD.format(id=id_, description=description))
    _append_roster(ROSTER_AGENT_ENTRY.format(id=id_))
    print(f"scaffolded primitives-core/agents/{id_}.md + roster row")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("type", choices=["skill", "agent"])
    p.add_argument("id")
    p.add_argument("--description", default=DEFAULT_DESCRIPTION)
    args = p.parse_args()
    if args.type == "skill":
        scaffold_skill(args.id, args.description)
    else:
        scaffold_agent(args.id, args.description)


if __name__ == "__main__":
    main()
