"""Opt-in handoff transactions, bound to the native hook's writer and tool call."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import shlex
import subprocess
import sys
import tempfile
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def contained(root, value):
    root = Path(root).resolve()
    candidate = root / value
    candidate.resolve().relative_to(root)
    if candidate.is_symlink():
        raise ValueError("handoff path is a symlink")
    return candidate.resolve()


def paths(root, config, harness, writer, native):
    if config.get("mode") != "external" or not config.get("stamp"):
        raise ValueError("session scope requires external mode and a contained stamp")
    if harness not in ("codex", "opencode") or not writer or not native or native == "unknown":
        raise ValueError("unsupported runtime or missing launch/native identity")
    base = contained(root, config["stamp"])
    key = digest([harness, writer, native])
    cert = contained(root, str(base.with_name(base.stem + "." + key + base.suffix)))
    return cert, contained(root, str(cert) + ".binding"), key


def read(path):
    with open(path, encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError("handoff record is not an object")
    return value


def write(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=Path(path).parent,
                                         delete=False) as target:
            temporary = Path(target.name)
            json.dump(value, target, sort_keys=True)
            target.flush()
            os.fsync(target.fileno())
        if read(temporary) != value:
            raise ValueError("handoff local readback failed")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def transcript_state(path):
    """Use the runtime log even when a hook cannot write its invalidation."""
    pending = set()
    last = None
    with open(path, encoding="utf-8") as source:
        for number, line in enumerate(source):
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("invalid runtime record")
            if item.get("type") != "response_item":
                continue
            body = item.get("payload", {})
            if not isinstance(body, dict):
                raise ValueError("invalid runtime response item")
            kind, call = body.get("type"), body.get("call_id")
            if kind in ("function_call", "custom_tool_call", "local_shell_call"):
                if not call:
                    raise ValueError("runtime tool call has no identity")
                last = [number, call]
                pending.add(call)
            elif kind in ("function_call_output", "custom_tool_call_output", "local_shell_call_output"):
                pending.discard(call)
    if last is None:
        raise ValueError("runtime has no tool transaction")
    return last, pending


def begin(root, config, payload):
    harness = os.environ.get("ATELIER_HARNESS", "claude")
    writer, native = os.environ.get("ATELIER_WRITER_ID"), payload.get("session_id")
    cert, binding, key = paths(root, config, harness, writer, native)
    epoch, pending = transcript_state(payload.get("transcript_path"))
    if epoch[1] != payload.get("tool_use_id") or pending != {epoch[1]}:
        raise ValueError("session handoff requires one sequential native tool transaction")
    value = {"root": str(Path(root).resolve()), "harness": harness, "writer": writer,
             "native": native, "key": key, "stamp": str(cert), "epoch": epoch,
             "transcript": payload["transcript_path"]}
    binding.parent.mkdir(parents=True, exist_ok=True)
    write(binding, value)
    cert.unlink(missing_ok=True)
    transaction = contained(root, str(binding) + "." + digest(epoch))
    write(transaction, value)
    return transaction


def check(root, config, payload, minutes, consume=False):
    cert, binding, _ = paths(root, config, os.environ.get("ATELIER_HARNESS", "claude"),
                             os.environ.get("ATELIER_WRITER_ID"), payload.get("session_id"))
    value, proof = read(binding), read(cert)
    epoch, pending = transcript_state(payload.get("transcript_path"))
    if proof.get("binding") != value or value.get("epoch") != epoch or pending:
        raise ValueError("handoff certificate does not cover the latest completed native tool")
    if not proof.get("card") or len(proof.get("body_sha256", "")) != 64:
        raise ValueError("handoff certificate has no persistence readback")
    if time.time() - cert.stat().st_mtime >= minutes * 60:
        raise ValueError("session handoff certificate is stale")
    if consume:
        cert.unlink()


def hook(root, config, payload, minutes=30):
    event = payload.get("hook_event_name")
    if event not in ("PreToolUse", "PreCompact"):
        return {}
    if event == "PreToolUse" and (os.environ.get("ATELIER_HARNESS") != "codex"
                                   or not os.environ.get("ATELIER_WRITER_ID")
                                   or not payload.get("session_id")):
        return {"systemMessage": "Session handoff unsupported: native Codex hooks and launch identity required. Ordinary tools remain available; manual compaction is uncertified."}
    try:
        if event == "PreToolUse":
            binding = begin(root, config, payload)
            output = {"hookEventName": event, "additionalContext": "Session handoff binding: " + str(binding)}
            tool_input = payload.get("tool_input", {})
            if payload.get("tool_name") == "Bash" and isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
                prefix = "export ATELIER_HANDOFF_BINDING=" + shlex.quote(str(binding))
                prefix += " ATELIER_TOOL_CALL_ID=" + shlex.quote(payload["tool_use_id"]) + "; "
                output["permissionDecision"] = "allow"
                output["updatedInput"] = dict(tool_input, command=prefix + tool_input["command"])
            return {"hookSpecificOutput": output}
        check(root, config, payload, minutes, consume=payload.get("trigger") == "manual")
        return {}
    except (OSError, ValueError, TypeError, KeyError) as error:
        message = "Session handoff uncertified: " + str(error) + ". Run the handoff persistence helper; do not compact on failure."
        if event == "PreToolUse":
            return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny",
                                           "permissionDecisionReason": message}}
        if payload.get("trigger") != "manual":
            return {"systemMessage": message}
        if os.environ.get("ATELIER_HARNESS") == "codex":
            return {"continue": False, "stopReason": message, "systemMessage": message}
        return {"decision": "block", "reason": message, "systemMessage": message}


def kata(project, *args):
    proc = subprocess.run(["kata", *args, "--project", project, "--json"],
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def repository(root):
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    return git("remote", "get-url", "origin"), git("branch", "--show-current")


def native_card(issue):
    metadata = issue.get("metadata", {})
    if issue["status"] != "open" or any(key.startswith("github") for key in metadata):
        raise ValueError("handoff destination must be an open native card")


def related_refs(record):
    own = record["issue"]["short_id"]
    return {side["short_id"] for link in record.get("links", [])
            for side in (link["from"], link["to"]) if side["short_id"] != own}


def discover(project, root, related=(), offset=0, page_size=10):
    """Scan all cards before slicing display; unknown relevance is never discarded."""
    repo, branch = repository(root)
    items = kata(project, "list", "--status", "open", "--label", "handoff", "--limit", "0")["issues"]
    rows = []
    for item in items:
        record = kata(project, "show", item["short_id"])
        issue = record["issue"]
        meta = issue.get("metadata", {})
        work = related_refs(record)
        relevance = "relevant" if meta.get("handoff.repository") == repo or work.intersection(related) else "unknown"
        rows.append({"card": issue["short_id"], "title": issue["title"], "relevance": relevance,
                     "writer": meta.get("handoff.writer"), "repository": meta.get("handoff.repository"),
                     "branch": meta.get("work.branch"), "related": sorted(work), "conflicts": []})
    # ponytail: pairwise conflict scan; index shared keys if board size makes this costly.
    for index, row in enumerate(rows):
        for other in rows[index + 1:]:
            if (row["writer"] and row["writer"] == other["writer"] or
                set(row["related"]).intersection(other["related"]) or
                row["repository"] == other["repository"] == repo and row["branch"] == other["branch"] == branch):
                row["conflicts"].append(other["card"])
                other["conflicts"].append(row["card"])
    rows.sort(key=lambda row: (not bool(row["conflicts"]), row["relevance"] != "relevant", row["card"]))
    if offset < 0 or page_size < 1:
        raise ValueError("offset must be nonnegative and page size positive")
    end = min(offset + page_size, len(rows))
    return {"total": len(rows), "rows": rows[offset:end], "remaining": max(0, len(rows) - end),
            "continuation": {"offset": end, "page_size": page_size} if end < len(rows) else None}


def persist(binding_path, project, body_file, title="Session handoff", labels=(), related=(), predecessor=None):
    binding = read(binding_path)
    root = binding["root"]
    binding_path = contained(root, str(binding_path))
    cert = contained(root, binding["stamp"])
    latest = contained(root, str(cert) + ".binding")
    if str(binding_path) != str(latest) + "." + digest(binding["epoch"]):
        raise ValueError("unexpected handoff binding path")
    native = os.environ.get("CODEX_THREAD_ID") if binding["harness"] == "codex" else os.environ.get("ATELIER_NATIVE_SESSION_ID")
    if binding["writer"] != os.environ.get("ATELIER_WRITER_ID") or binding["native"] != native:
        raise ValueError("tool identity differs from authoritative hook binding")
    if binding["epoch"][1] != os.environ.get("ATELIER_TOOL_CALL_ID"):
        raise ValueError("tool call differs from authoritative hook binding")
    def current():
        if read(latest) != binding:
            raise ValueError("a later native tool invalidated this handoff transaction")
        if binding.get("concurrent"):
            raise ValueError("concurrent native tools cannot certify a handoff")
        if binding["harness"] == "codex":
            epoch, pending = transcript_state(binding["transcript"])
            if epoch != binding["epoch"] or pending != {epoch[1]}:
                raise ValueError("handoff requires the current sequential native tool")
    current()
    cert.unlink(missing_ok=True)
    body = Path(body_file).read_text(encoding="utf-8").strip()
    if not body:
        raise ValueError("refusing an empty handoff body")
    items = kata(project, "list", "--status", "all", "--limit", "0", "--meta", "handoff.writer=" + binding["key"])["issues"]
    if len(items) > 1:
        raise ValueError("multiple cards claim this writer; reconcile before writing")
    repo, branch = repository(root)
    metadata = {"handoff.writer": binding["key"], "handoff.native": native,
                "handoff.harness": binding["harness"], "handoff.host": socket.gethostname(),
                "handoff.worktree": root, "handoff.repository": repo, "work.branch": branch,
                "handoff.lifecycle": "active"}
    refs = set(related)
    if predecessor:
        prior_record = kata(project, "show", predecessor)
        prior = prior_record["issue"]
        if (any(key.startswith("github") for key in prior.get("metadata", {})) or
            not any(label.get("label") == "handoff" for label in prior_record.get("labels", []))):
            raise ValueError("predecessor must be a native handoff card")
        metadata["handoff.predecessor"] = prior["short_id"]
        refs.add(prior["short_id"])
    refs = {kata(project, "show", ref)["issue"]["short_id"] for ref in refs}
    if items:
        issue = kata(project, "show", items[0]["short_id"])["issue"]
        native_card(issue)
        args = ["edit", issue["short_id"], "--body", body]
        for ref in sorted(refs):
            args += ["--related", ref]
        kata(project, *args)
        for key, value in metadata.items():
            kata(project, "meta", "set", issue["short_id"], key, value)
    else:
        args = ["create", title, "--body", body, "--idempotency-key", "handoff-" + binding["key"], "--label", "handoff"]
        for key, value in metadata.items():
            args += ["--meta", key + "=" + value]
        for label in labels:
            args += ["--label", label]
        for ref in sorted(refs):
            args += ["--related", ref]
        issue = kata(project, *args)["issue"]
    record = kata(project, "show", issue["short_id"])
    verified = record["issue"]
    native_card(verified)
    if (verified.get("body") != body or
        any(verified.get("metadata", {}).get(key) != value for key, value in metadata.items()) or
        not refs.issubset(related_refs(record))):
        raise ValueError("native card readback differs from persisted handoff")
    current()
    proof = {"binding": binding, "card": verified["short_id"], "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
    write(cert, proof)
    return {"card": verified["short_id"], "certificate": str(cert)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["persist", "discover"])
    parser.add_argument("--binding", default=os.environ.get("ATELIER_HANDOFF_BINDING"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--body-file")
    parser.add_argument("--root", default=".")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--title", default="Session handoff")
    parser.add_argument("--label", action="append", default=[])
    parser.add_argument("--related", action="append", default=[])
    parser.add_argument("--predecessor")
    args = parser.parse_args()
    try:
        if args.command == "discover":
            print(json.dumps(discover(args.project, args.root, args.related, args.offset, args.page_size)))
            return 0
        if not args.binding or not args.body_file:
            parser.error("persist requires --binding and --body-file")
        print(json.dumps(persist(args.binding, args.project, args.body_file, args.title,
                                 args.label, args.related, args.predecessor)))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        print("Session handoff failed; do not compact: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
