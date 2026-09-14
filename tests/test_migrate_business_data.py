import contextlib
import hashlib
import io
import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "evals"))
import migrate_business_data as migration


class FakePB:
    def __init__(self, nonempty=False):
        self.nonempty = nonempty
        self.created = []

    def list_all(self, collection):
        return [{"id": "already-there"}] if self.nonempty else []

    def create(self, collection, body):
        self.created.append((collection, body))
        return {"id": body["id"]}


class BatchPB(FakePB):
    def __init__(self, response):
        super().__init__()
        self.response = response

    def _req(self, *_args):
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class MultipartPB(FakePB):
    def __init__(self):
        super().__init__()
        self.upload = None

    def create_multipart(self, collection, body, files):
        self.upload = (collection, body, files)
        return {"id": body["id"]}


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "data.db"
        self.storage = root / "storage"
        self.storage.mkdir()
        con = sqlite3.connect(self.db)
        con.execute("create table frameworks (id text, created text, updated text, body text)")
        con.execute("insert into frameworks values ('fw0000000000001', 'old', 'old', 'RAW-SENTINEL')")
        con.execute("create table extenders (id text, source text)")
        con.execute("insert into extenders values ('ex0000000000001', 'missing-source')")
        con.execute("create table artifacts (id text, sha256 text, blob text, created text, updated text)")
        con.execute("insert into artifacts values ('ar0000000000001', ?, 'blob.txt', 'old', 'old')",
                    (hashlib.sha256(b"actual").hexdigest(),))
        con.commit()
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rejects_system_auth_tables(self):
        with self.assertRaises(ValueError):
            migration.validate_scope_tables(("frameworks", "users"))

    def test_missing_relation_is_rejected(self):
        with self.assertRaises(ValueError):
            migration.read_export(self.db, self.storage, ("extenders",))

    def test_dry_run_never_leaks_row_content(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            export = migration.read_export(self.db, self.storage, ("frameworks",))
            migration.print_receipt(migration.receipt(export))
        self.assertNotIn("RAW-SENTINEL", out.getvalue())
        self.assertIn('"frameworks":{"count":1', out.getvalue())

    def test_default_scope_excludes_telemetry(self):
        self.assertNotIn("runs", migration.scope_tables("core"))

    def test_scope_tuples_are_exact(self):
        self.assertEqual(("frameworks", "sources", "extenders", "framework_elements", "files", "distributions", "frontmatter_dimensions", "eval_runs", "eval_responses", "assessments", "job_coverage", "relationships"), migration.CORE)
        self.assertEqual(("runs", "artifacts", "run_events", "tool_calls"), migration.TELEMETRY)
        self.assertEqual(migration.CORE + migration.TELEMETRY, migration.ALL)

    def test_missing_multi_relation_is_rejected(self):
        con = sqlite3.connect(self.db)
        con.execute("create table distributions (id text, members text)")
        con.execute("insert into distributions values ('di0000000000001', '[\"missing\"]')")
        con.execute("create table extenders2 (id text)")
        con.commit()
        con.close()
        with self.assertRaises(ValueError):
            migration._validate_relations({"distributions": [{"id": "di0000000000001", "members": ["missing"]}], "extenders": []}, ("distributions", "extenders"))

    def test_artifact_hash_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            migration.read_export(self.db, self.storage, ("artifacts",))

    def test_artifact_resolution_is_literal_and_rejects_unsafe_names(self):
        nested = self.storage / "nested"
        nested.mkdir()
        (nested / "blob.txt").write_bytes(b"literal")
        self.assertEqual(b"literal", migration._artifact_bytes(self.storage, "blob.txt"))
        for name in ("../blob.txt", "nested/blob.txt", "nested\\blob.txt", ".", "..", "*.txt", "?.txt", "[a].txt"):
            with self.assertRaises(ValueError):
                migration._artifact_bytes(self.storage, name)

    def test_artifact_resolution_rejects_symlink_matches(self):
        outside = Path(self.tmp.name) / "outside.txt"
        outside.write_bytes(b"outside")
        (self.storage / "outside-link.txt").symlink_to(outside)
        inside = self.storage / "inside.txt"
        inside.write_bytes(b"inside")
        (self.storage / "inside-link.txt").symlink_to(inside)
        for name in ("outside-link.txt", "inside-link.txt"):
            with self.assertRaises(ValueError):
                migration._artifact_bytes(self.storage, name)

    def test_apply_refuses_nonempty_destination_before_writes(self):
        export = migration.Export({"frameworks": [{"id": "fw0000000000001", "body": "x"}]}, {})
        pb = FakePB(nonempty=True)
        with self.assertRaises(ValueError):
            migration.apply_export(pb, export, ("frameworks",))
        self.assertEqual([], pb.created)

    def test_private_receipt_is_exclusive_and_owner_only(self):
        destination = Path(self.tmp.name) / "receipt.json"
        export = migration.Export({"frameworks": [{"id": "fw0000000000001", "created": "old", "updated": "old"}]}, {})
        migration.write_private_receipt(destination, export, migration.receipt(export))
        self.assertEqual(0o600, stat.S_IMODE(destination.stat().st_mode))
        with self.assertRaises(ValueError):
            migration.write_private_receipt(destination, export, migration.receipt(export))

    def test_batch_requires_top_level_successful_matching_ids(self):
        rows = [{"id": "fw0000000000001"}]
        migration._batch_create(BatchPB([{"status": 200, "body": {"id": rows[0]["id"]}}]), "frameworks", rows)
        for response in ({"responses": []}, [{"status": 500, "body": {"id": rows[0]["id"]}}], [{"status": 200, "body": {"id": "wrong"}}]):
            with self.assertRaises(migration.MigrationError):
                migration._batch_create(BatchPB(response), "frameworks", rows)

    def test_apply_error_hides_raw_exception_content(self):
        with self.assertRaises(migration.MigrationError) as caught:
            migration._batch_create(BatchPB(RuntimeError("RAW-SENTINEL")), "frameworks", [{"id": "fw0000000000001"}])
        self.assertNotIn("RAW-SENTINEL", str(caught.exception))

    def test_post_validation_rejects_wrong_destination_content(self):
        export = migration.Export({"frameworks": [{"id": "fw0000000000001", "body": "expected", "created": "old", "updated": "old"}]}, {})
        pb = FakePB()
        pb.list_all = lambda _collection: [{"id": "fw0000000000001", "body": "wrong"}]
        with self.assertRaises(migration.MigrationError):
            migration.verify_destination(pb, export, ("frameworks",))

    def test_post_validation_rejects_wrong_id_count_and_relation(self):
        export = migration.Export({"files": [{"id": "fi0000000000001", "extender": "ex0000000000001", "content": "x"}]}, {})
        cases = (
            [{"id": "wrong", "extender": "ex0000000000001", "content": "x"}],
            [],
            [{"id": "fi0000000000001", "extender": "wrong", "content": "x"}],
        )
        for destination in cases:
            pb = FakePB()
            pb.list_all = lambda _collection, value=destination: value
            with self.assertRaises(migration.MigrationError):
                migration.verify_destination(pb, export, ("files",))

    def test_artifact_upload_uses_verified_original_bytes(self):
        blob = b"exact verified bytes"
        row = {"id": "ar0000000000001", "blob": "blob.bin", "sha256": hashlib.sha256(blob).hexdigest(), "created": "old", "updated": "old"}
        pb = MultipartPB()
        with patch.object(migration, "verify_destination", return_value={}):
            migration.apply_export(pb, migration.Export({"artifacts": [row]}, {row["id"]: blob}), ("artifacts",))
        self.assertEqual(blob, pb.upload[2]["blob"][1])

    def test_artifact_readback_hash_mismatch_is_rejected(self):
        blob = b"expected"
        row = {"id": "ar0000000000001", "blob": "blob.bin", "sha256": hashlib.sha256(blob).hexdigest()}
        pb = FakePB()
        pb.list_all = lambda _collection: [{"id": row["id"]}]
        pb._req = lambda *_args: {"token": "safe-token"}
        with patch.object(migration, "_download_artifact", return_value=b"wrong"):
            with self.assertRaises(migration.MigrationError):
                migration.verify_destination(pb, migration.Export({"artifacts": [row]}, {row["id"]: blob}), ("artifacts",))

    def test_receipt_digest_ignores_audit_and_artifact_transport(self):
        source = migration.Export({"artifacts": [{"id": "ar0000000000001", "sha256": "hash", "blob": "source.bin", "created": "old", "updated": "old", "kind": "tool_output"}]}, {})
        destination = migration.Export({"artifacts": [{"id": "ar0000000000001", "sha256": "hash", "blob": "renamed.bin", "created": "fresh", "updated": "fresh", "kind": "tool_output"}]}, {})
        self.assertEqual(migration.receipt(source)["tables"], migration.receipt(destination)["tables"])
        destination.rows["artifacts"][0]["kind"] = "screenshot"
        self.assertNotEqual(migration.receipt(source)["tables"], migration.receipt(destination)["tables"])

    def test_source_boolean_fields_normalize_only_zero_one_and_bools(self):
        self.assertIs(False, migration._decode(0, "is_binary", "files"))
        self.assertIs(True, migration._decode(1, "is_binary", "files"))
        self.assertIs(False, migration._decode(False, "is_binary", "files"))
        self.assertIs(True, migration._decode(True, "is_binary", "files"))
        for value in (2, "0", None):
            with self.assertRaises(ValueError):
                migration._decode(value, "is_binary", "files")

    def test_current_retirement_field_normalizes_as_boolean(self):
        self.assertIs(False, migration._decode(0, "retired", "extenders"))
        self.assertIs(True, migration._decode(1, "retired", "extenders"))

    def test_destination_integer_bool_does_not_match_canonical_body(self):
        export = migration.Export({"sources": [{"id": "so0000000000001", "publishes_evals": False}]}, {})
        pb = FakePB()
        pb.list_all = lambda _collection: [{"id": "so0000000000001", "publishes_evals": 0}]
        with self.assertRaises(migration.MigrationError):
            migration.verify_destination(pb, export, ("sources",))


if __name__ == "__main__":
    unittest.main()
