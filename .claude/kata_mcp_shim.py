#!/usr/bin/env python3
"""stdio proxy: kata mcp serve -> Claude Code, with root schema composition removed.

The Anthropic Messages API rejects tool input_schema with oneOf/allOf/anyOf at
the root, and Claude Code silently drops such tools. Root `not` and `if/then`
are accepted, so `allOf` made only of those is hoisted; anything else at the
root is stripped. The server still validates every call against its own
schema, and the daemon enforces close rules, so nothing is lost but guidance.

Usage in .mcp.json: command python3, args [<this file>, --all-projects].
Extra args pass straight through to `kata mcp serve`.
"""
import json
import subprocess
import sys
import threading

# Constraints that vanish from the schema, restated where the model can see them.
HINTS = {
    "kata.close": " Rules: reason=done needs a message of 40+ chars and 1+ evidence of type "
                  "commit/pr/test/reviewed-paths; wontfix needs 60+ chars and evidence []; "
                  "duplicate and superseded need 20+ chars and exactly one duplicate-of / "
                  "superseded-by; audit-no-change needs 40+ chars and exactly one no-change-audit.",
    "kata.set_deadline": " Pass exactly one of deadline or clear_deadline=true.",
    "kata.set_schedule": " Pass exactly one of schedule or clear_schedule=true.",
}


def flatten(schema):
    parts = schema.pop("allOf", [])
    schema.pop("oneOf", None)
    schema.pop("anyOf", None)
    nots = [p["not"] for p in parts if set(p) == {"not"}]
    conds = [p for p in parts if "if" in p and set(p) <= {"if", "then", "else"}]
    if nots:
        schema["not"] = nots[0] if len(nots) == 1 else {"anyOf": nots}
    if len(conds) == 1:
        schema.update(conds[0])
    # ponytail: >1 if/then or mixed allOf is dropped, not hoisted; kata has none today.
    return schema


def rewrite(line):
    try:
        msg = json.loads(line)
        tools = msg["result"]["tools"]
    except (ValueError, KeyError, TypeError):
        return line
    for t in tools:
        if isinstance(t.get("inputSchema"), dict):
            flatten(t["inputSchema"])
        if t.get("name") in HINTS:
            t["description"] = t.get("description", "") + HINTS[t["name"]]
    return json.dumps(msg, separators=(",", ":")) + "\n"


def main():
    child = subprocess.Popen(["kata", "mcp", "serve", *sys.argv[1:]], stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, text=True, bufsize=1)

    def pump_in():
        for line in sys.stdin:
            child.stdin.write(line)
            child.stdin.flush()
        child.stdin.close()

    threading.Thread(target=pump_in, daemon=True).start()
    for line in child.stdout:
        sys.stdout.write(rewrite(line))
        sys.stdout.flush()
    sys.exit(child.wait())


if __name__ == "__main__":
    main()
