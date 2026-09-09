#!/usr/bin/env python3
"""Version-bump gate — changed published bytes must ship under a moved version.

Consumers install plugins by version and cache them, so publishing changed content under
an unchanged version reaches nobody: the release is a silent no-op. The expensive shape is
the DUAL-HOMED one. `plugins/<id>/` are thin symlink assemblies over `primitives-core/`
(ADR 0017), so editing one skill body changes the published bytes of EVERY plugin that
ships it — bump none of them and every gate stays green while no installed machine ever
receives the fix.

What this proves, per plugin listed in `plugins/`:

  1. The assembly DEREFERENCED to real bytes (symlinks followed, exactly what
     `.github/workflows/publish.yml` lifts with `cp -RL plugins`) is compared, path by
     path, against that same plugin as published on `origin/main`.
  2. The comparison runs in BOTH directions — a path only the working tree has (added) and
     a path only the published tree has (removed) each count as a change, not just a
     content difference on a shared path.
  3. When anything differs, `plugins/<id>/.claude-plugin/plugin.json`'s `version` must
     differ from the published manifest's. An unmoved version is the violation.

`main` is a FILTERED, PARENTED assembly, never a snapshot of `dev`: its `plugins/` are
dereferenced regular files where `dev`'s are symlinks, and nothing else from `dev` is on
it. So this never whole-tree diffs the two branches — only plugin subtrees, dereferenced
against published.

Where it runs: a step in the `drift guards` CI job, NOT in `make ci`. Reaching
`origin/main` needs NETWORK, and `make ci` is offline-and-zero-install by design; a new CI
job was equally unavailable because `dev`'s branch protection pins required checks by job
NAME, so adding one would strand every open PR on a check that never reports (owner
ruling, TASK-032).

Network contract — uniform across every CI-only gate here (decision-016 point 4): a gate
that cannot measure is red, never green, so no usable published ref at all exits 1 saying
outright that it is not evidence of a missing bump. The ref is fetched best-effort into
`refs/remotes/origin/main` and resolved by that FULL refname, never by the short
`origin/main`: the short form is AMBIGUOUS, and git resolves `refs/<name>`,
`refs/tags/<name>` and `refs/heads/<name>` BEFORE `refs/remotes/<name>`, so a local branch
or tag literally named `origin/main` would otherwise become the published tree this gate
compares against — silently, since `--quiet` suppresses git's ambiguity warning and the
fetch still updates the tracking ref nobody read. The short form survives only in message
text, where it is what a reader recognises.

FRESHNESS IS CONTACT WITH THE REMOTE — not the age of the commit the ref points at. A
fetch that exits 0 rewrote the tracking ref from `origin` moments ago, so it is current by
definition however old that commit is: a quiet `main` publishes nothing for weeks and its
cache is no less accurate for it. When the fetch FAILS, the comparison falls back to the
cached ref and warns, because something real was still compared — but only while THIS
CLONE's last successful sync is no more than `MAX_SYNC_AGE_DAYS` (7) days old, so an
indefinitely stale cache cannot mask a real unbumped change forever without the gate going
red. That moment is recorded here, in a one-line stamp under the git common directory,
because git records nothing equivalent (measured on git 2.55.0: a fetch that finds nothing
new writes NO reflog entry for the tracking ref; `.git/FETCH_HEAD` is truncated and
re-dated by a FAILED fetch exactly as by a successful one, so its mtime dates the last
ATTEMPT, not the last sync; and `git clone` leaves neither for `refs/remotes/origin/main`).
No stamp, an unreadable one, or one dated in the FUTURE — a clock disagreeing rather than a
fresh sync — is red on the same rule: freshness unproven is freshness unmeasured. A clone
that has never synced under this gate therefore cannot use the fallback until it runs once
with a reachable remote, which is one command and the honest verdict meanwhile.

The stamp names the URL it was earned from, and a sync earned from a DIFFERENT remote is
no record at all: that fetch wrote the cached ref too, so a fork's tree would otherwise
carry a seven-day freshness certificate the canonical remote never issued. The stamp does
NOT name the sha it synced to. That would additionally catch a tracking ref moved by
something other than this gate — a hand `git update-ref`, or a fetch with an explicit
refspec — but a plain `git pull` moves that ref legitimately between gate runs, so a
sha-bound stamp would go red on ordinary use; and anyone able to write the tracking ref by
hand can write the stamp beside it, so it buys no guarantee against a local actor. A stamp
in the older bare-timestamp format cannot name a remote, so it reads as unreadable rather
than being grandfathered: honouring it would keep exactly the hazard above alive for seven
days on every clone that ran the previous version.

The gate assumes `origin` resolves to the canonical publish remote and does NOT check it.
A contributor whose `origin` is a fork or any stale mirror gets a successful fetch of the
wrong tree and a green that measured the wrong thing — online and, since the stamp is
earned in that same configuration, offline too. Verifying the URL against a known-good
value would hardcode a consuming repo's convention, which AGENTS.md forbids without an
override, so the assumption is stated rather than enforced; a check would have to arrive
through `docs/override-convention.md`, not a hardcoded URL. Comparing the stamp's remote
against the CURRENT one hardcodes nothing — it only requires the two to agree.

A full local clone is never shallow-marked as a side effect (`--depth=1` is used only where
the repo is already shallow, as in a CI checkout).

Deliberately NOT covered: parity between `plugin.json` and the root
`.claude-plugin/marketplace.json` entry, which `scripts/check_catalog.py` already enforces
(`version_problems()`) in the same CI job — with it, a bump proven here in `plugin.json`
must appear in `marketplace.json` too, and a disagreement between the two is red there.
Also not covered: version ORDERING (a version that moved backwards is a distinct version,
so consumers still refetch); file modes; a plugin published on `main` but deleted on `dev`
(a removal has no version to bump); and anything outside `plugins/`.

**NO SEMVER SEMANTICS, by design (decision-017).** This gate proves MOVEMENT and nothing
else: it never reads major/minor/patch, so passing here says nothing about whether the digit
that moved was the right one. Which digit a dual-homed change earns — owning bundle minor,
carrying bundle patch, both minor for genuinely new capability in both, never "incidental"
for a breaking change — is convention enforced by review and stated in the `publish-to-main`
skill, where a session reads it before bumping. Grading a digit would require inferring
capability from bytes, which this gate cannot see, so it deliberately does not try. Do not
read a green here as digit coverage, and do not "fix" that by teaching it semver.

Paths matching the ignore rules that can appear in a dereferenced walk (`__pycache__/`,
`*.pyc`, editor/OS noise) are pruned from BOTH sides — `cp -RL` copies them but `git add`
never commits them, so leaving them in produces phantom diffs.

Stdlib-only, deterministic. Exit 0 = the published tree was read and every plugin is clean;
exit 1 = violations (prints every one), or a published tree that could not be read at all.
Usage: python3 scripts/check_version_bump.py   (run from anywhere)
"""

import hashlib
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(REPO, "plugins")

PUBLISHED_REMOTE = "origin"
PUBLISHED_BRANCH = "main"
# The short form is for MESSAGES — it is what a reader recognises. Every git command uses
# the full one, which no local branch or tag can shadow.
PUBLISHED_REF = f"{PUBLISHED_REMOTE}/{PUBLISHED_BRANCH}"
PUBLISHED_FULL_REF = f"refs/remotes/{PUBLISHED_REMOTE}/{PUBLISHED_BRANCH}"
PUBLISHED_PREFIX = "plugins"
MANIFEST_REL = os.path.join(".claude-plugin", "plugin.json")
GIT_TIMEOUT_SECONDS = 120
# How long this clone's last successful sync of the published ref may stand in for a
# refreshed one after a failed fetch. Longer than any plausible offline stretch, short
# enough that a cache cannot silently outlive the published tree it claims to represent.
MAX_SYNC_AGE_DAYS = 7
SECONDS_PER_DAY = 86400
# Where that sync is recorded: one line, unix seconds, under the git COMMON dir, so linked
# worktrees share the record exactly as they share the remote-tracking ref it describes.
SYNC_STAMP_NAME = "version-bump-published-sync"

# Mirrors the .gitignore rules that can surface inside a dereferenced plugins/ walk:
# `cp -RL` copies them onto the publish tree, `git add -A` then drops them, so they are
# never published and must not be compared.
PRUNE_DIRS = frozenset({"__pycache__", ".ruff_cache"})
PRUNE_NAMES = frozenset({".DS_Store"})
PRUNE_SUFFIXES = (".pyc", ".pyo", ".swp")

MAX_LISTED_PATHS = 5  # per direction, in one violation message
MAX_GIT_ERROR_CHARS = 200  # git's fetch stderr is multi-line and long; keep the notice one line


def is_pruned(name):
    """True for a path component that never reaches the published tree."""
    return (
        name in PRUNE_DIRS
        or name in PRUNE_NAMES
        or name.endswith(PRUNE_SUFFIXES)
    )


def _one_line(text, limit=MAX_GIT_ERROR_CHARS):
    """Squash git's multi-line stderr into one bounded line fit for a CI notice."""
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def blob_hash(data, algo="sha1"):
    """The git object id of `data` as a blob — comparable to `git ls-tree`'s column 3."""
    h = hashlib.new(algo)
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


# --- the working tree, dereferenced -------------------------------------------------

def local_index(plugins_dir=None, algo="sha1"):
    """{plugin id: {relpath: blob hash}} for `plugins/`, symlinks followed.

    This is the publish lift (`cp -RL plugins`) computed in process: symlinked skill,
    agent and hook bodies are read as the real bytes they resolve to, which is what makes
    a dual-homed edit visible under every plugin that ships it.
    """
    base = plugins_dir or PLUGINS_DIR
    index = {}
    if not os.path.isdir(base):
        return index
    for pid in sorted(os.listdir(base)):
        pdir = os.path.join(base, pid)
        if is_pruned(pid) or not os.path.isdir(pdir):
            continue
        index[pid] = _walk_blobs(pdir, algo)
    return index


def _walk_blobs(pdir, algo="sha1"):
    """{relpath: blob hash} for every unpruned file under `pdir`, symlinks followed."""
    blobs = {}
    seen_dirs = set()
    for dirpath, dirs, files in os.walk(pdir, followlinks=True):
        # A symlinked directory could in principle point back up the tree; realpath
        # bookkeeping keeps the dereferencing walk finite regardless of the assembly.
        real = os.path.realpath(dirpath)
        if real in seen_dirs:
            dirs[:] = []
            continue
        seen_dirs.add(real)
        dirs[:] = sorted(d for d in dirs if not is_pruned(d))
        for name in sorted(files):
            if is_pruned(name):
                continue
            full = os.path.join(dirpath, name)
            try:
                with open(full, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue  # a broken symlink; scripts/check_symlinks.py owns that failure
            rel = os.path.relpath(full, pdir).replace(os.sep, "/")
            blobs[rel] = blob_hash(data, algo)
    return blobs


def local_plugin_json(pid, plugins_dir=None):
    """Raw bytes of plugins/<pid>/.claude-plugin/plugin.json, or None if absent."""
    path = os.path.join(plugins_dir or PLUGINS_DIR, pid, MANIFEST_REL)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


# --- the published tree, via git ----------------------------------------------------

def run_git(args, repo=None, timeout=GIT_TIMEOUT_SECONDS):
    """Run git in `repo`; return (returncode, stdout bytes, stderr text)."""
    proc = subprocess.run(
        ["git", "-C", repo or REPO] + list(args), capture_output=True, timeout=timeout
    )
    return proc.returncode, proc.stdout, proc.stderr.decode("utf-8", "replace").strip()


def parse_ls_tree(out):
    """Parse `git ls-tree -r -z <ref> -- plugins` into {pid: {relpath: blob hash}}.

    Entries are `<mode> SP <type> SP <objectid> TAB <path> NUL`. Bytes in, decoded with
    surrogateescape, so a path carrying non-ASCII bytes survives intact rather than
    tripping the decoder (the failure check_flow.py hit on its own tracked-path parse).
    """
    index = {}
    for raw in out.split(b"\0"):
        if not raw:
            continue
        head, _, path_bytes = raw.partition(b"\t")
        if not path_bytes:
            continue
        fields = head.split()
        if len(fields) < 3 or fields[1] != b"blob":
            continue  # submodule/commit entries carry no comparable content
        oid = fields[2].decode("ascii")
        path = path_bytes.decode("utf-8", "surrogateescape")
        parts = path.split("/")
        if len(parts) < 3 or parts[0] != PUBLISHED_PREFIX:
            continue
        if any(is_pruned(p) for p in parts):
            continue
        index.setdefault(parts[1], {})["/".join(parts[2:])] = oid
    return index


class GitPublishedTree:
    """The published plugins as they exist on `origin/main`, read through git.

    `prepare()` is the network step and the only one that can decline: it returns None when
    the ref is usable (leaving an advisory `note`), or a human-readable reason string when
    the published tree cannot be reached at all.

    Every git command names `PUBLISHED_FULL_REF`; `self.ref` is the short form and belongs
    in messages only. `stamp_path` is injectable so the sync record can be driven without
    a real git dir.
    """

    def __init__(self, ref=PUBLISHED_REF, repo=None, run=None, stamp_path=None):
        self.ref = ref
        self.repo = repo or REPO
        self.note = ""
        self._run = run or (lambda args: run_git(args, repo=self.repo))
        self._sha = None
        self._fetch_error = ""
        self._stamp_path = stamp_path

    def _git(self, args):
        return self._run(list(args))

    def prepare(self):
        try:
            self._fetch()
            # Existence by exact ref path first: `rev-parse --verify` applies all six
            # resolution rules even to a full refname, so with no tracking ref a local
            # branch named `refs/remotes/origin/main` would become the published tree.
            rc, out, _ = self._git(["show-ref", "--verify", "--quiet", PUBLISHED_FULL_REF])
            if rc == 0:
                # A second call because `show-ref` takes no `^{commit}` suffix.
                rc, out, _ = self._git(
                    ["rev-parse", "--verify", "--quiet", f"{PUBLISHED_FULL_REF}^{{commit}}"]
                )
            if rc != 0 or not out.strip():
                detail = f" ({self._fetch_error})" if self._fetch_error else ""
                return f"{self.ref} could not be resolved{detail}"
            self._sha = out.decode("ascii", "replace").strip()
            # A ref just rewritten from the remote is current by definition, so the sync
            # record is only worth reading — and only capable of declining — on the
            # fallback path, where no contact was made.
            if self._fetch_error:
                return self._unsynced_reason()
        except FileNotFoundError:
            return "git is not available on PATH, so the published tree cannot be read"
        except subprocess.TimeoutExpired:
            return (
                f"reading {self.ref} timed out after {GIT_TIMEOUT_SECONDS}s — the published "
                "tree could not be read"
            )
        return None

    @property
    def stamp_path(self):
        """Where this clone's sync record lives, resolved once through git."""
        if self._stamp_path is None:
            rc, out, _ = self._git(["rev-parse", "--git-common-dir"])
            gitdir = out.decode("utf-8", "replace").strip() if rc == 0 else ""
            if gitdir and not os.path.isabs(gitdir):
                # git resolves it against the directory it ran in, which is `self.repo`.
                gitdir = os.path.join(self.repo, gitdir)
            self._stamp_path = os.path.join(gitdir, SYNC_STAMP_NAME) if gitdir else ""
        return self._stamp_path

    def _remote_url(self):
        """What `origin` resolves to right now, rewrites applied; "" if unreadable."""
        rc, out, _ = self._git(["remote", "get-url", PUBLISHED_REMOTE])
        return out.decode("utf-8", "replace").strip() if rc == 0 else ""

    def _record_sync(self):
        """Record that the published ref was just rewritten, and from WHERE."""
        url = self._remote_url()
        if not self.stamp_path or not url:
            return  # a record that cannot name its remote certifies nothing
        try:
            with open(self.stamp_path, "w") as fh:
                fh.write("%d\t%s\n" % (int(time.time()), url))
        except OSError:
            pass  # a read-only git dir only costs the NEXT offline run its fallback

    def _read_sync(self):
        """(unix seconds, problem) for a sync earned from the remote `origin` names NOW.

        A record from any other remote is no record: the fetch that wrote it also wrote
        the cached ref, so both describe a tree the current `origin` never published.
        """
        if not self.stamp_path:
            return None, "this clone's git directory could not be located"
        try:
            with open(self.stamp_path) as fh:
                raw = fh.read().strip()
        except FileNotFoundError:
            return None, (
                "this clone has no record of ever syncing it (run this gate once with the "
                "remote reachable)"
            )
        except OSError as exc:
            return None, f"its sync record could not be read ({exc.strerror})"
        stamped_at, _, stamped_url = raw.partition("\t")
        try:
            seconds = int(stamped_at) if stamped_url else None
        except ValueError:
            seconds = None
        if seconds is None:
            return None, f"its sync record is unreadable ({_one_line(raw, 40)!r})"
        url = self._remote_url()
        if not url:
            return None, f"the URL `{PUBLISHED_REMOTE}` resolves to could not be read"
        if url != stamped_url:
            return None, (
                f"the only sync on record was earned from {stamped_url}, not from the "
                f"{url} that `{PUBLISHED_REMOTE}` names now"
            )
        return seconds, None

    def _unsynced_reason(self):
        """Reason string when no recent-enough sync backs the cached ref.

        Also finishes the fallback warning with the measured age, so a reader of the green
        path can judge what the comparison was worth.
        """
        synced_at, problem = self._read_sync()
        if problem:
            return (
                f"{self.ref} could not be refreshed ({self._fetch_error}) and {problem}, so "
                "the cached ref's freshness is unproven"
            )
        age_days = (time.time() - synced_at) / SECONDS_PER_DAY
        # A NEGATIVE age is a clock disagreeing with the one that wrote the stamp, not a
        # fresh sync: a clock moved backwards would otherwise report a long-abandoned
        # record as comfortably within the limit. Unmeasured either way, so red either way
        # — but described as unproven rather than as past the limit, which it is not.
        if age_days < 0:
            return (
                f"{self.ref} could not be refreshed ({self._fetch_error}) and its sync "
                f"record is dated {-age_days:.2f} days in the FUTURE (a clock disagreeing, "
                "not a fresh sync), so the cached ref's freshness is unproven"
            )
        if age_days > MAX_SYNC_AGE_DAYS:
            return (
                f"{self.ref} could not be refreshed ({self._fetch_error}) and this clone "
                f"last synced it {age_days:.2f} days ago, past the {MAX_SYNC_AGE_DAYS}-day "
                "limit — too stale to stand in for what is published now"
            )
        # Two decimals in both verdicts: one would print "7.0 days ago" on either side of
        # the cutoff, leaving a CI log unable to say which way it went.
        self.note += (
            f" (last synced {age_days:.2f} days ago, within the {MAX_SYNC_AGE_DAYS}-day limit)"
        )
        return None

    def _fetch(self):
        """Best-effort refresh of the published ref; records why it failed, never raises."""
        self._fetch_error = ""
        self.note = ""  # per-attempt state: a warning must not outlive the failure it named
        args = ["fetch", "--quiet", "--no-tags"]
        rc, out, _ = self._git(["rev-parse", "--is-shallow-repository"])
        # Only deepen-free fetch a repo that is ALREADY shallow (a CI checkout). Passing
        # --depth=1 to a complete clone would shallow-mark a contributor's repo as a side
        # effect of running a read-only gate.
        if rc == 0 and out.strip() == b"true":
            args.append("--depth=1")
        args += [
            PUBLISHED_REMOTE,
            f"+refs/heads/{PUBLISHED_BRANCH}:refs/remotes/{PUBLISHED_REMOTE}/{PUBLISHED_BRANCH}",
        ]
        rc, _, err = self._git(args)
        if rc != 0:
            self._fetch_error = _one_line(err) or f"git fetch exited {rc}"
            self.note = (
                f"{self.ref} could not be refreshed ({self._fetch_error}); comparing against "
                "the locally cached ref"
            )
            return
        self._record_sync()

    def index(self):
        rc, out, err = self._git(
            ["ls-tree", "-r", "-z", self._sha or PUBLISHED_FULL_REF, "--", PUBLISHED_PREFIX]
        )
        if rc != 0:
            raise RuntimeError(f"git ls-tree {self.ref} failed: {err}")
        return parse_ls_tree(out)

    def plugin_json(self, pid):
        rel = f"{PUBLISHED_PREFIX}/{pid}/.claude-plugin/plugin.json"
        rc, out, _ = self._git(
            ["cat-file", "blob", f"{self._sha or PUBLISHED_FULL_REF}:{rel}"]
        )
        return out if rc == 0 else None


# --- the comparison -----------------------------------------------------------------

def _version(raw, where):
    """(version, problem) for a plugin.json's bytes — either side of the comparison."""
    if raw is None:
        return None, f"{where}: missing — cannot verify the version bump"
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return None, f"{where}: unparseable JSON ({exc}) — cannot verify the version bump"
    version = obj.get("version")
    if not isinstance(version, str) or not version.strip():
        return None, f"{where}: no usable `version` field — cannot verify the version bump"
    return version, None


def _listed(paths):
    shown = sorted(paths)[:MAX_LISTED_PATHS]
    more = len(paths) - len(shown)
    return ", ".join(shown) + (f", +{more} more" if more else "")


def _delta(local_blobs, published_blobs):
    """(changed, added, removed) path sets — the comparison run in BOTH directions."""
    local_paths, published_paths = set(local_blobs), set(published_blobs)
    changed = {p for p in local_paths & published_paths if local_blobs[p] != published_blobs[p]}
    return changed, local_paths - published_paths, published_paths - local_paths


def compare(local, published, local_json, published_json):
    """Return one violation string per plugin whose published bytes moved but version did not.

    `local` and `published` are {pid: {relpath: blob hash}} indexes; `local_json` and
    `published_json` are callables taking a plugin id and returning that side's raw
    plugin.json bytes (or None). Injecting the two sides keeps the rule testable without
    git, a network, or the real tree.
    """
    problems = []
    for pid in sorted(local):
        if pid not in published:
            continue  # a first release cannot have a previous version to move
        changed, added, removed = _delta(local[pid], published[pid])
        if not (changed or added or removed):
            continue

        where = f"{PUBLISHED_PREFIX}/{pid}"
        local_version, problem = _version(local_json(pid), f"{where}/.claude-plugin/plugin.json")
        if problem:
            problems.append(problem)
            continue
        published_version, problem = _version(
            published_json(pid), f"{PUBLISHED_REF}:{where}/.claude-plugin/plugin.json"
        )
        if problem:
            problems.append(problem)
            continue
        if local_version != published_version:
            continue

        detail = []
        if changed:
            detail.append(f"changed: {_listed(changed)}")
        if added:
            detail.append(f"added: {_listed(added)}")
        if removed:
            detail.append(f"removed: {_listed(removed)}")
        problems.append(
            f"{where}: published bytes differ from {PUBLISHED_REF} but the version stayed "
            f"{local_version!r} — consumers cache by version, so this ships nothing "
            f"({'; '.join(detail)})"
        )
    return problems


def main(plugins_dir=None, tree=None, out=print):
    tree = tree if tree is not None else GitPublishedTree()
    reason = tree.prepare()
    if reason:
        out(
            f"✗ version-bump guard: {reason}. Nothing was compared, so this is NOT evidence "
            "of a missing version bump — it is a gate that could not measure, which "
            "decision-016 point 4 makes red rather than green. Re-run once the published "
            "tree is readable."
        )
        return 1
    if getattr(tree, "note", ""):
        out(f"⚠ version-bump guard: {tree.note}")

    problems = compare(
        local_index(plugins_dir),
        tree.index(),
        lambda pid: local_plugin_json(pid, plugins_dir),
        tree.plugin_json,
    )
    if problems:
        out(f"✗ version-bump guard: {len(problems)} violation(s)")
        for p in problems:
            out(f"  - {p}")
        out(
            "  Bump the plugin's `version` in plugins/<id>/.claude-plugin/plugin.json AND in "
            "the matching .claude-plugin/marketplace.json entry (scripts/check_catalog.py "
            "holds the two in parity)."
        )
        return 1
    out(
        f"✓ version-bump guard clean — every plugin's dereferenced bytes either match "
        f"{PUBLISHED_REF} or ship under a moved version"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
