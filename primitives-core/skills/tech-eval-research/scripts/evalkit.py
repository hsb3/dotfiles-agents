"""Shared core of the eval kit scripts: error types, configuration, paths and loading."""
import argparse
import json
import re
import sys
from pathlib import Path

# tomllib (3.11+) and yaml are imported where used, so --help works on any Python without them.
# Artifact locations relative to the project root; eval.toml may override any of them.
DEFAULTS = {
    "spec_dir": "data",
    "schemas_dir": "schemas",
    "findings_dir": "data/findings",
    "proofs_glob": "runs/*/runs.jsonl",
    "db": "eval.db",
}
# Optional table: old artifact path prefix -> new prefixes to try, for run logs recorded before a move.
MOVES_KEY = "artifact_moves"
# Used when the project has no schemas dir and eval.toml does not name one.
BUNDLED_SCHEMAS = Path(__file__).resolve().parents[1] / "references" / "schemas"


class EvalError(Exception):
    """A user-facing problem, printed as `path:location: message`."""

    exit_code = 2

    def __init__(self, path, message, location=None):
        super().__init__(message)
        self.path, self.message, self.location = path, message, location

    def __str__(self):
        loc = "" if self.location is None else f":{self.location}"
        return f"{self.path}{loc}: {self.message}"


class ConfigError(EvalError):
    """Bad --root, eval.toml content or schema file."""


class MissingArtifactError(EvalError):
    """A required file does not exist."""


class ParseError(EvalError):
    """A file is not valid YAML, JSON or TOML, or cannot be read."""


class SchemaViolation(EvalError):
    """An artifact does not match its schema."""

    exit_code = 1


class ReferenceMismatch(EvalError):
    """An id is unknown, duplicated or missing, or a weight set disagrees with the spec."""

    exit_code = 1


class Project:
    def __init__(self, root: Path):
        self.root = root
        settings = dict(DEFAULTS)
        self.artifact_moves = {}
        data = {}
        toml_path = root / "eval.toml"
        if toml_path.is_file():
            import tomllib

            try:
                data = tomllib.loads(self.read(toml_path))
            except tomllib.TOMLDecodeError as e:
                # Every supported Python ends the message with "(at line L, column C)".
                m = re.fullmatch(r"(.*) \(at line (\d+), column (\d+)\)", str(e))
                raise ParseError("eval.toml", f"invalid TOML: {m[1] if m else e}",
                                 f"{m[2]}:{m[3]}" if m else None) from None
            moves = data.pop(MOVES_KEY, {})
            unknown = sorted(set(data) - set(DEFAULTS))
            if unknown:
                raise ConfigError("eval.toml", f"unknown key(s) {unknown}; allowed: {sorted([*DEFAULTS, MOVES_KEY])}")
            self.artifact_moves = self.check_moves(moves)
            for key, value in data.items():
                if not isinstance(value, str) or not value:
                    raise ConfigError("eval.toml", f"{key} must be a non-empty string")
            if Path(data.get("proofs_glob", "x")).is_absolute():
                raise ConfigError("eval.toml", "proofs_glob must be relative to the project root")
            settings.update(data)
        self.spec = root / settings["spec_dir"]
        self.schemas = root / settings["schemas_dir"]
        if "schemas_dir" not in data and not self.schemas.exists():
            self.schemas = BUNDLED_SCHEMAS
        self.findings = root / settings["findings_dir"]
        self.proofs_glob = settings["proofs_glob"]
        self.db = root / settings["db"]

    @staticmethod
    def check_moves(moves):
        def bad(why):
            return ConfigError("eval.toml", f"{MOVES_KEY} {why}")

        if not isinstance(moves, dict):
            raise bad("must be a table of old prefix = [new prefixes]")
        def prefix(x):
            # Whole folders only (trailing /), inside the project (relative, no ..).
            return isinstance(x, str) and x.endswith("/") and x != "/" and not Path(x).is_absolute() and ".." not in Path(x).parts

        for old, new in moves.items():
            if not prefix(old):
                raise bad(f"key {old!r} must be a relative folder prefix ending in / without ..")
            if not isinstance(new, list) or not new:
                raise bad(f"{old!r} must be a non-empty list of path prefixes")
            for n in new:
                if not prefix(n):
                    raise bad(f"{old!r}: {n!r} must be a relative folder prefix ending in / without ..")
        return moves

    def artifact_exists(self, a: str) -> bool:
        """True when a, or a under any moved prefix from eval.toml artifact_moves, exists."""
        tries = [a] + [n + a[len(old):] for old, new in self.artifact_moves.items() if a.startswith(old) for n in new]
        return any((self.root / t).exists() for t in tries)

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)

    def findings_files(self):
        return sorted(self.findings.glob("*.yaml"))

    def runs_files(self):
        return sorted(self.root.glob(self.proofs_glob))

    def read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise MissingArtifactError(self.rel(path), "required file is missing") from None
        except (OSError, UnicodeDecodeError) as e:
            raise ParseError(self.rel(path), f"cannot read: {e}") from None

    def yaml(self, path: Path):
        import yaml

        text = self.read(path)
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            raise ParseError(self.rel(path), f"invalid YAML: {getattr(e, 'problem', None) or e}",
                             None if mark is None else f"{mark.line + 1}:{mark.column + 1}") from None

    def jsonl(self, path: Path):
        """(line number, record) for each non-blank line; ParseError at the first invalid one."""
        records = []
        for n, line in enumerate(self.read(path).splitlines(), 1):
            if line.strip():
                try:
                    records.append((n, json.loads(line)))
                except json.JSONDecodeError as e:
                    raise ParseError(self.rel(path), f"invalid JSON ({e.msg})", n) from None
        return records


def run(body, description, argv=None) -> int:
    """Parse --root, run body(project) -> list of EvalError, print them, return the exit code."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--root", type=Path, default=Path.cwd(),
                    help="project root (default: the current directory)")
    args = ap.parse_args(argv)
    if sys.version_info < (3, 11):
        sys.stderr.write("validation needs Python >= 3.11 (tomllib)\n")
        return 2
    try:
        if not args.root.is_dir():
            raise ConfigError(str(args.root), "project root is not a directory")
        errors = body(Project(args.root.resolve()))
    except EvalError as e:
        errors = [e]
    for e in errors:
        print(e, file=sys.stderr)
    if not errors:
        return 0
    print(f"{len(errors)} error(s)", file=sys.stderr)
    return max(e.exit_code for e in errors)
