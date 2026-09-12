#!/usr/bin/env python3
"""Offline, fixed-scope transfer of the private business-record backup.

The default operation is a read-only receipt.  ``--apply`` is deliberately
guarded for the root operator; it copies no source credentials or auth state.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


CORE = (
    "frameworks", "sources", "extenders", "framework_elements", "files",
    "distributions", "frontmatter_dimensions", "eval_runs", "eval_responses",
    "assessments", "job_coverage", "relationships",
)
TELEMETRY = ("runs", "artifacts", "run_events", "tool_calls")
ALL = CORE + TELEMETRY
FORBIDDEN = {"_superusers", "users", "_collections", "_params", "coverage_gaps"}

# Fixed schema relations.  Each target must be in the selected import and each
# nonempty reference must name a selected source record.
RELATIONS = {
    "framework_elements": {"framework": "frameworks"},
    "extenders": {"source": "sources"},
    "files": {"extender": "extenders"},
    "distributions": {"members": "extenders"},
    "frontmatter_dimensions": {"spec_framework": "frameworks"},
    "eval_runs": {"frameworks": "frameworks"},
    "eval_responses": {"run": "eval_runs", "extenders": "extenders"},
    "assessments": {"extender": "extenders", "framework": "frameworks",
                    "element": "framework_elements", "eval_run": "eval_runs"},
    "job_coverage": {"job": "framework_elements", "source": "sources", "eval_run": "eval_runs"},
    "relationships": {"extender_a": "extenders", "extender_b": "extenders",
                      "job": "framework_elements", "eval_run": "eval_runs"},
    "artifacts": {"run": "runs"},
    "run_events": {"run": "runs", "artifact": "artifacts"},
    "tool_calls": {"run": "runs", "artifact": "artifacts"},
}
JSON_FIELDS = {
    "extenders": {"requires", "frontmatter"},
    "eval_responses": {"response_json"},
    "runs": {"checks", "grades", "tool_names", "model_usage", "provenance"},
    "run_events": {"payload"}, "tool_calls": {"input", "output"},
}
MULTI_FIELDS = {"frameworks": {"applies_to"}, "sources": {"publishes"},
                "distributions": {"members"}, "eval_runs": {"frameworks"},
                "eval_responses": {"extenders"}}


@dataclass
class Export:
    rows: dict
    artifacts: dict
    artifact_sidecars: int = 0


class MigrationError(RuntimeError):
    """A destination-operation failure whose text cannot expose remote content."""


def _destination_error(operation, collection):
    return MigrationError(f"destination {operation} failed for {collection}")


def scope_tables(scope):
    return {None: CORE, "core": CORE, "telemetry": TELEMETRY, "all": ALL}[scope]


def validate_scope_tables(tables):
    unknown = set(tables) - set(ALL)
    forbidden = set(tables) & FORBIDDEN
    if unknown or forbidden:
        raise ValueError("scope contains a non-business table")


def _connect(source_db):
    uri = Path(source_db).resolve().as_uri() + "?mode=ro&immutable=1"
    return sqlite3.connect(uri, uri=True)


def _decode(value, field, collection):
    if value is None or field not in JSON_FIELDS.get(collection, set()) | MULTI_FIELDS.get(collection, set()):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid structured field in {collection}") from exc
    return value


def _rows(connection, table):
    try:
        columns = [r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')]
        if not columns:
            raise ValueError(f"missing selected business table: {table}")
        data = connection.execute(f'SELECT * FROM "{table}"').fetchall()
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"cannot read selected business table: {table}") from exc
    return sorted(({key: _decode(value, key, table) for key, value in zip(columns, row)}
                   for row in data), key=lambda row: row["id"])


def _ids(value):
    if value in (None, "", []):
        return []
    return value if isinstance(value, list) else [value]


def _validate_relations(rows, tables):
    ids = {name: {row["id"] for row in data} for name, data in rows.items()}
    for collection, fields in RELATIONS.items():
        if collection not in rows:
            continue
        for field, target in fields.items():
            if not rows[collection] or field not in rows[collection][0]:
                continue
            if target not in tables:
                raise ValueError(f"selected {collection} requires omitted business collection")
            for row in rows[collection]:
                if any(record_id not in ids[target] for record_id in _ids(row.get(field))):
                    raise ValueError(f"missing selected relation in {collection}")


def _artifact_name(blob):
    values = _ids(blob)
    if len(values) != 1 or not isinstance(values[0], str) or values[0].endswith(".attrs"):
        raise ValueError("invalid artifact blob reference")
    return values[0]


def _artifact_bytes(storage, name):
    matches = [p for p in Path(storage).rglob(name) if p.is_file() and not p.name.endswith(".attrs")]
    if len(matches) != 1:
        raise ValueError("artifact blob could not be resolved")
    return matches[0].read_bytes()


def _digest(rows):
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def read_export(source_db, storage, tables):
    validate_scope_tables(tables)
    with _connect(source_db) as connection:
        rows = {table: _rows(connection, table) for table in tables}
    _validate_relations(rows, tables)
    artifacts = {}
    for row in rows.get("artifacts", []):
        content = _artifact_bytes(storage, _artifact_name(row.get("blob")))
        actual = hashlib.sha256(content).hexdigest()
        if actual != row.get("sha256"):
            raise ValueError("artifact hash mismatch")
        artifacts[row["id"]] = content
    return Export(rows, artifacts, sum(1 for path in Path(storage).rglob("*.attrs") if path.is_file()))


def receipt(export):
    tables = {name: {"count": len(rows), "sha256": _digest(rows)} for name, rows in export.rows.items()}
    blob_bytes = sum(len(value) for value in export.artifacts.values())
    files = export.rows.get("files", [])
    file_stats = {"file_size_bytes": sum(row.get("size_bytes") or 0 for row in files),
                  "file_stored_hashes": len({row.get("sha256") for row in files if row.get("sha256")}),
                  "file_nonempty_content": sum(bool(row.get("content")) for row in files)}
    return {"tables": tables, "total": sum(x["count"] for x in tables.values()),
            "artifact_blobs": len(export.artifacts), "artifact_bytes": blob_bytes,
            "artifact_sidecars": export.artifact_sidecars,
            "artifact_sha256": _digest({key: hashlib.sha256(value).hexdigest() for key, value in export.artifacts.items()}),
            **file_stats}


def print_receipt(value):
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def write_private_receipt(path, export, value):
    path = Path(path)
    audit = {table: [{"id": row["id"], "created": row.get("created"), "updated": row.get("updated")}
                    for row in rows] for table, rows in export.rows.items()}
    hashes = {record_id: hashlib.sha256(blob).hexdigest() for record_id, blob in export.artifacts.items()}
    payload = json.dumps({"receipt": value, "audit": audit, "artifact_hashes": hashes},
                         sort_keys=True, separators=(",", ":")) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError("refusing to overwrite receipt") from None
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(payload)


def _body(row):
    return {key: value for key, value in row.items() if key not in {"created", "updated", "blob"}}


def _batch_create(pb, collection, rows):
    for start in range(0, len(rows), 10):
        requests = [{"method": "POST", "url": f"/api/collections/{collection}/records", "body": _body(row)}
                    for row in rows[start:start + 10]]
        try:
            results = pb._req("POST", "/api/batch", {"requests": requests})
        except Exception:
            raise _destination_error("batch create", collection) from None
        if not isinstance(results, list) or len(results) != len(requests):
            raise _destination_error("batch create", collection)
        if any(not isinstance(item, dict) or not 200 <= item.get("status", 0) < 300
               or not isinstance(item.get("body"), dict)
               or item["body"].get("id") != row["id"]
               for item, row in zip(results, rows[start:start + 10])):
            raise _destination_error("batch create", collection)


def _download_artifact(pb, collection, record_id, filename, token):
    url = f"{pb.base}/api/files/{collection}/{record_id}/{urllib.parse.quote(filename)}?token={urllib.parse.quote(token)}"
    with urllib.request.urlopen(urllib.request.Request(url)) as response:
        return response.read()


def verify_destination(pb, export, tables):
    copied = {}
    artifact_rows = {}
    for collection in tables:
        try:
            destination = pb.list_all(collection)
        except Exception:
            raise _destination_error("readback", collection) from None
        source = export.rows[collection]
        if len(destination) != len(source) or {row.get("id") for row in destination} != {row["id"] for row in source}:
            raise _destination_error("readback validation", collection)
        by_id = {row["id"]: row for row in destination}
        if collection == "artifacts":
            artifact_rows = by_id
        normalized = []
        for source_row in source:
            expected = _body(source_row)
            actual = {key: by_id[source_row["id"]].get(key) for key in expected}
            if actual != expected:
                raise _destination_error("readback validation", collection)
            normalized.append(actual)
        copied[collection] = normalized
    if "artifacts" in tables:
        try:
            token_response = pb._req("POST", "/api/files/token", {})
            token = token_response.get("token") if isinstance(token_response, dict) else None
            if not token:
                raise ValueError()
        except Exception:
            raise _destination_error("file token", "artifacts") from None
        for row in export.rows["artifacts"]:
            try:
                blob = _download_artifact(pb, "artifacts", row["id"],
                                          _artifact_name(artifact_rows[row["id"]].get("blob")), token)
            except Exception:
                raise _destination_error("artifact download", "artifacts") from None
            if blob != export.artifacts[row["id"]] or hashlib.sha256(blob).hexdigest() != row["sha256"]:
                raise _destination_error("artifact validation", "artifacts")
    return receipt(Export(copied, export.artifacts, export.artifact_sidecars))


def apply_export(pb, export, tables):
    for collection in tables:
        try:
            nonempty = pb.list_all(collection)
        except Exception:
            raise _destination_error("emptiness check", collection) from None
        if nonempty:
            raise ValueError("destination business collection is not empty")
    for collection in tables:
        if collection == "artifacts":
            for row in export.rows[collection]:
                blob = export.artifacts[row["id"]]
                try:
                    result = pb.create_multipart(collection, _body(row), {"blob": (_artifact_name(row["blob"]), blob, row.get("mime") or "application/octet-stream")})
                except Exception:
                    raise _destination_error("artifact create", collection) from None
                if not isinstance(result, dict) or result.get("id") != row["id"]:
                    raise _destination_error("artifact create", collection)
        else:
            _batch_create(pb, collection, export.rows[collection])
    return verify_destination(pb, export, tables)


def main(argv=None):
    parser = argparse.ArgumentParser(description="offline business-data receipt/import")
    parser.add_argument("--source-db", required=True)
    parser.add_argument("--storage")
    parser.add_argument("--scope", choices=("core", "telemetry", "all"), default="core")
    parser.add_argument("--receipt")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    storage = args.storage or str(Path(args.source_db).parent / "storage")
    export = read_export(args.source_db, storage, scope_tables(args.scope))
    value = receipt(export)
    print_receipt(value)
    if args.receipt:
        write_private_receipt(args.receipt, export, value)
    if args.apply:
        from pb import PB
        print_receipt(apply_export(PB(), export, scope_tables(args.scope)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
