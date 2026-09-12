import contextlib
import hashlib
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

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
        self.assertNotIn("runs", migration.scope_tables(None))

    def test_artifact_hash_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            migration.read_export(self.db, self.storage, ("artifacts",))

    def test_apply_refuses_nonempty_destination_before_writes(self):
        export = migration.Export({"frameworks": [{"id": "fw0000000000001", "body": "x"}]}, {})
        pb = FakePB(nonempty=True)
        with self.assertRaises(ValueError):
            migration.apply_export(pb, export, ("frameworks",))
        self.assertEqual([], pb.created)


if __name__ == "__main__":
    unittest.main()
