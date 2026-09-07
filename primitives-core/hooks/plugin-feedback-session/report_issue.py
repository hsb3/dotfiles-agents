#!/usr/bin/env python3
"""report_issue.py — the plugin-feedback reporter.

Files a defect report about a plugin from this marketplace as one consistently shaped issue,
so an agent that noticed something mid-task does not free-hand a `gh issue create`
and land a malformed title, an ad-hoc body, or the wrong label.

The template is the shape the ad-hoc field observations already converged on:
plugin name + version, the consuming project, the date, symptom + repro, a severity
and the contract-violation (bug) or limitation (feature) check, the workaround, and
an optional suggested fix.

Tier rule (ratified doctrine, carried by the two companion hooks):
  - a bug may be filed by any session, including a dispatched worker — the bar is
    objective, `observed behavior contradicts the plugin's own stated contract`;
  - a feature request is filed by the primary session only. A dispatched worker runs
    `--draft`, prints the body, and hands it to its dispatcher to review and file.

`--draft` prints the report and files nothing, but it does run the membership check
below, which costs one gh read whenever no marketplace manifest sits near the plugin
root (the normal case for an installed plugin). A target repo it cannot resolve, or a
read it cannot make, still gets its draft.

Scope, checked and not merely described: this reporter files into the marketplace it
shipped from, NOT into the repo of the plugin being reported. `--plugin` is matched
against that marketplace's own `.claude-plugin/marketplace.json`, and an id it does not
list is refused (`--allow-unlisted` is the deliberate way past) because such a report
would land in front of maintainers who cannot fix it. A list that cannot be determined
at all waives the check with a notice: a network blip must not swallow a report. Both
hooks scope their offer the same way, and the resolved target is printed with its
provenance before anything is filed, so the destination is never something the caller
has to infer.

The target repo is DATA, never a literal in this file: `PLUGIN_FEEDBACK_REPO` wins,
otherwise it is read from the reporting plugin's own manifest
(`<plugin-root>/.claude-plugin/plugin.json` -> `repository`), which is the sanctioned
place for a plugin's authorship and origin metadata. Neither one resolvable is a
refusal that names the variable, never a guess.

The label is DATA too: the per-kind default is matched against the target repo's live
label set before filing, so a rename costs a notice and an unlabelled issue rather than
a failed call. The unlabelled retry below stays the backstop for what that check cannot
see (a label deleted between the two calls, a repo gh cannot list).

gh itself is the one external dependency, and it is checked where it is run rather than
described: absent from PATH, filing stops with a message naming gh and pointing at
`--draft`, which still works because a read it cannot make was already allowed to
degrade to `unknown`.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and must
stay compatible with Python 3.9.

Usage:
  python3 report_issue.py bug --plugin <id> --plugin-version <v> \\
      --summary "<outcome in plain language>" --symptom "<what happens>" \\
      --repro "<steps>" --contract "<the stated contract it contradicts>"
  python3 report_issue.py feature --plugin <id> --plugin-version <v> \\
      --summary "<outcome>" --symptom "<what is missing>" \\
      --limitation "<the limitation actually hit>" --draft
"""

import argparse
import collections
import datetime
import json
import os
import re
import subprocess
import sys

KIND_BUG = "bug"
KIND_FEATURE = "feature"
KINDS = (KIND_BUG, KIND_FEATURE)

SEVERITIES = ("blocker", "major", "minor")
# Least severe on purpose: a filer who never thought about severity must not claim
# urgency it has not earned. An under-marked report costs one upgrade at read time; a
# queue where every report arrives `major` carries no priority signal at all.
DEFAULT_SEVERITY = SEVERITIES[-1]

# Env surfaces. The repo variable is the documented escape hatch for a marketplace
# whose plugins do not carry a `repository` in their manifest.
REPO_ENV = "PLUGIN_FEEDBACK_REPO"
LABEL_ENV = {
    KIND_BUG: "PLUGIN_FEEDBACK_LABEL_BUG",
    KIND_FEATURE: "PLUGIN_FEEDBACK_LABEL_FEATURE",
}
DEFAULT_LABELS = {KIND_BUG: "type:fix", KIND_FEATURE: "type:feat"}

# gh fails the whole `issue create` when a label is missing, AFTER the body is composed —
# so a stale default costs the filer their report and buys a re-run. Matching this lets the
# report land unlabelled instead, which is recoverable; a lost report is not.
LABEL_MISSING = re.compile(r"could not add label", re.I)

# gh pages label lists. A response filling the page may be a truncated one, and a label
# set read short would strip a label that does exist — so a full page reads as unknown.
LABEL_PAGE = 200

# The marketplace roster, in the one spelling both readers below need: a relative path
# under a checkout root, and a path inside the target repo for the gh read.
MARKETPLACE_MANIFEST = ".claude-plugin/marketplace.json"
ALLOW_UNLISTED = "--allow-unlisted"

# The reporter's one external dependency. Filing without it is impossible, so the
# message names it and points at the path that still works — a draft the filer can hand
# to someone who has gh, rather than a report they have to compose again.
GH_MISSING = (
    "report_issue: gh is not on PATH, so nothing was filed — this reporter files "
    "through the GitHub CLI. Install gh (or put it on PATH), or rerun with --draft to "
    "print the report and file it by hand.\n"
)

NO_FIX = "None offered."
NO_REPRO = "Not captured."
NO_WORKAROUND = "None known."

# Printed on both output paths. The boundary is the reporter's, not the reported
# plugin's: a defect in a plugin from another marketplace belongs in that project's
# own tracker, and this line is what lets a reader catch it heading the wrong way.
SCOPE_NOTE = (
    "this reporter files into the marketplace it shipped from, not the reported "
    "plugin's own repo"
)

SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")

Report = collections.namedtuple(
    "Report",
    "kind plugin plugin_version project date severity summary symptom "
    "repro contract limitation workaround fix",
)
Report.__new__.__defaults__ = ("", "", "", "", "")  # repro contract limitation workaround fix


# ---------------------------------------------------------------------------
# Target repo (data, not a literal)
# ---------------------------------------------------------------------------

def normalize_repo(value):
    """Reduce a repository value to `owner/name`, or None if it is not one.

    Accepts the three forms a manifest realistically carries: an `owner/name` slug,
    an https URL, and an scp-style git remote. A dict is read for its `url` key,
    which is how package-manifest conventions spell the same field.
    """
    if isinstance(value, dict):
        value = value.get("url") or value.get("repository") or ""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v:
        return None
    if v.endswith(".git"):
        v = v[:-4]
    v = v.rstrip("/")
    if ":" in v and "//" not in v:
        # scp-style remote, <user>@<host>:owner/name — the placeholder stays bracketed
        # so no line in this file has the shape of a real remote (the tests ban it).
        v = v.split(":", 1)[1]
    v = v.split("://", 1)[-1]  # drop any scheme
    parts = [p for p in v.split("/") if p]
    if len(parts) < 2:
        return None
    owner, name = parts[-2], parts[-1]
    if not SEGMENT.match(owner) or not SEGMENT.match(name):
        return None
    return owner + "/" + name


def _manifest_repo(plugin_root):
    """The `repository` recorded in a plugin's own manifest, or None."""
    if not plugin_root:
        return None
    path = os.path.join(plugin_root, ".claude-plugin", "plugin.json")
    try:
        with open(path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    except Exception:
        return None
    if not isinstance(manifest, dict):
        return None
    return normalize_repo(manifest.get("repository"))


def _default_plugin_root():
    """This file's plugin root: <root>/hooks/<hook-dir>/report_issue.py."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def resolve_repo(env, plugin_root=None):
    """`PLUGIN_FEEDBACK_REPO` first, else the plugin manifest's `repository`."""
    override = (env.get(REPO_ENV) or "").strip()
    if override:
        return normalize_repo(override)
    root = plugin_root or env.get("CLAUDE_PLUGIN_ROOT") or _default_plugin_root()
    return _manifest_repo(root)


def target_origin(env):
    """Which surface the target repo came from, in words a reader can act on."""
    if (env.get(REPO_ENV) or "").strip():
        return REPO_ENV
    return "this plugin's own manifest"


def describe_target(repo, env):
    """`owner/name (from <surface>)` — the destination, spelled out, never implicit.

    Both output paths print this before anything leaves the machine: the target is
    resolved from data the caller cannot see, and a report about a plugin from another
    marketplace resolving here is exactly the mistake this line makes visible.
    """
    if not repo:
        return "unresolved (set {0} to owner/name)".format(REPO_ENV)
    return "{0} (from {1})".format(repo, target_origin(env))


def resolve_label(kind, env, override=None):
    """An explicit `--label` wins, then the per-kind env var, then the default."""
    if override:
        return override
    from_env = (env.get(LABEL_ENV[kind]) or "").strip()
    return from_env or DEFAULT_LABELS[kind]


class GhUnavailable(Exception):
    """gh could not be started at all — raised by `_run_gh`, by nothing else."""


def _run_gh(argv, runner):
    """The single place this reporter runs gh. Every call routes through here.

    A runner raises OSError (FileNotFoundError) when the binary is absent, and that is
    the one failure no caller can tell from gh's own non-zero exit unless it is named
    here — so it is separated once, at the shared point, rather than guarded at each
    call site where the next read added would miss the guard.

    The policy on it differs by caller, which is why this raises rather than deciding:
    a READ degrades to unknown (a missing binary is one more read that cannot be made,
    like a blip or a rate limit, and a draft is still owed to its filer), while the
    FILING path stops with the message below because nothing can be filed without gh.
    """
    try:
        return runner(argv, text=True, capture_output=True)
    except OSError as exc:
        raise GhUnavailable(exc)


def _gh_json(argv, runner):
    """Parsed stdout of a read-only gh call, or None on any failure at all."""
    try:
        done = _run_gh(argv, runner)
    except Exception:
        return None
    if getattr(done, "returncode", 1) != 0:
        return None
    try:
        return json.loads(getattr(done, "stdout", "") or "")
    except Exception:
        return None


def live_labels(repo, runner):
    """The labels the target repo actually carries, or None when gh cannot say.

    None is `unknown`, never `empty`: the caller leaves the label alone on it, so an
    unanswerable read can only ever skip the check, never strip a working label.
    """
    names = _gh_json([
        "gh", "label", "list", "--repo", repo,
        "--json", "name", "--limit", str(LABEL_PAGE),
    ], runner)
    if not isinstance(names, list) or len(names) >= LABEL_PAGE:
        return None
    live = set(
        e["name"] for e in names
        if isinstance(e, dict) and isinstance(e.get("name"), str)
    )
    return live or None


def unlabelled_notice(label, repo, kind):
    """One wording for both ways a label drops out — the pre-check and the retry."""
    return (
        "report_issue: label {0!r} not found in {1} — filing unlabelled; "
        "set {2} to a label that repo carries.\n".format(label, repo, LABEL_ENV[kind])
    )


# ---------------------------------------------------------------------------
# Marketplace membership — the scope boundary as a check, not a paragraph
# ---------------------------------------------------------------------------

def _listed_ids(data):
    """The plugin ids a parsed marketplace manifest carries, or None if it has none."""
    entries = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return None
    ids = sorted(set(
        e["name"] for e in entries
        if isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"]
    ))
    return ids or None


def _local_marketplace_ids(root):
    """Nearest marketplace manifest at or above `root` — free, offline, tried first.

    A source checkout finds the tree's own manifest this way. An installed plugin root
    (<marketplace>/<plugin>/<version>/) carries a plugin manifest but no marketplace
    one, so that caller finds nothing here and falls through to the gh read.

    Bounded at the enclosing repo root: a manifest ABOVE the checkout belongs to some
    other tree that happens to contain this one, and reading it would answer a question
    about this marketplace with someone else's roster.
    """
    path = os.path.abspath(root or os.curdir)
    while True:
        candidate = os.path.join(path, *MARKETPLACE_MANIFEST.split("/"))
        if os.path.isfile(candidate):
            try:
                with open(candidate, encoding="utf-8") as fh:
                    return _listed_ids(json.load(fh))
            except Exception:
                return None
        if os.path.exists(os.path.join(path, ".git")):
            return None
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def _remote_marketplace_ids(repo, runner):
    """The target repo's own marketplace manifest, read raw through gh.

    gh rather than anything on disk: the target repo is already resolved and gh is
    already this reporter's hard dependency, while an installed plugin root carries no
    marketplace manifest to read.
    """
    if not repo:
        return None
    return _listed_ids(_gh_json([
        "gh", "api", "-H", "Accept: application/vnd.github.raw",
        "repos/{0}/contents/{1}".format(repo, MARKETPLACE_MANIFEST),
    ], runner))


def membership(plugin, env, repo, runner):
    """`(allowed, listed)` — `listed` is None when membership is undeterminable.

    A manifest found on disk may only ever ALLOW: whatever sits near the plugin root on
    this machine is not necessarily this marketplace, so a local miss consults the target
    repo before it can cost anyone a refusal. That buys the rare refusal one gh call, and
    a wrong refusal is far more expensive than the call.
    """
    local = _local_marketplace_ids(env.get("CLAUDE_PLUGIN_ROOT") or _default_plugin_root())
    if local and plugin in local:
        return True, local
    listed = _remote_marketplace_ids(repo, runner) or local
    if listed is None:
        return True, None
    return plugin in listed, listed


def membership_refusal(plugin, listed):
    """Why a report about a plugin from elsewhere is not filed here."""
    return (
        "report_issue: {0!r} is not a plugin this marketplace ships, so a report about "
        "it would land in front of maintainers who cannot fix it — file it in that "
        "project's own tracker instead. Shipped here: {1}. If the id is right and the "
        "manifest is stale, rerun with {2}.\n".format(
            plugin, ", ".join(listed), ALLOW_UNLISTED
        )
    )


# ---------------------------------------------------------------------------
# The template
# ---------------------------------------------------------------------------

def build_title(report):
    """`component: outcome in plain language` — the shape issue intake expects."""
    return "{0}: {1}".format(report.plugin.strip(), report.summary.strip())


def build_body(report):
    """Render the fixed template. Deterministic: every value comes off the report."""
    version = report.plugin_version.strip() or "unspecified"
    facts = [
        "- **Plugin:** {0} {1}".format(report.plugin.strip(), version),
        "- **Consuming project:** {0}".format(report.project.strip() or "unspecified"),
        "- **Observed:** {0}".format(report.date.strip()),
        "- **Severity:** {0}".format(report.severity.strip()),
    ]
    if report.kind == KIND_BUG:
        facts.append("- **Contract violated:** {0}".format(report.contract.strip()))
    else:
        facts.append("- **Limitation hit:** {0}".format(report.limitation.strip()))

    sections = [
        "## Field observation",
        "",
        "\n".join(facts),
        "",
        "## What happens",
        "",
        report.symptom.strip(),
        "",
        "## Repro",
        "",
        report.repro.strip() or NO_REPRO,
        "",
        "## Workaround",
        "",
        report.workaround.strip() or NO_WORKAROUND,
        "",
        "## Suggested fix",
        "",
        report.fix.strip() or NO_FIX,
        "",
        "---",
        "",
        "Filed from an agent session with the plugin-feedback reporter.",
    ]
    return "\n".join(sections) + "\n"


def build_argv(repo, title, body, label):
    """The gh invocation this reporter makes. A falsy label omits the flag entirely —
    the unlabelled retry below, not a caller's normal path."""
    argv = [
        "gh", "issue", "create",
        "--repo", repo,
        "--title", title,
        "--body", body,
    ]
    if label:
        argv += ["--label", label]
    return argv


def render_draft(report, title, body, label, target):
    """A draft a dispatcher can read and file, with the filing command spelled out."""
    return "\n".join([
        "DRAFT — not filed. Hand this to your dispatcher to review and file.",
        "",
        "Repo:  {0}".format(target),
        "Scope: {0}".format(SCOPE_NOTE),
        "Label: {0}".format(label),
        "Title: {0}".format(title),
        "",
        body.rstrip("\n"),
        "",
        "File it by rerunning this command without --draft.",
        "",
    ])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="report_issue.py",
        description=(
            "File a defect report about a plugin from this marketplace, to a fixed "
            "template. Issues go to the marketplace this reporter shipped from, not to "
            "the reported plugin's own repo; the resolved target is printed before "
            "anything is filed."
        ),
    )
    p.add_argument("kind", choices=KINDS, help="bug (any session) or feature (primary session)")
    p.add_argument("--plugin", required=True, help="the plugin the report is about")
    p.add_argument("--plugin-version", required=True, help="its version, from its plugin manifest")
    p.add_argument("--summary", required=True, help="the outcome, in plain language, for the title")
    p.add_argument("--symptom", required=True, help="what happens (bug) or what is missing (feature)")
    p.add_argument("--project", default="", help="the consuming project (default: this directory)")
    p.add_argument("--date", default="", help="observation date (default: today)")
    p.add_argument(
        "--severity",
        choices=SEVERITIES,
        default=DEFAULT_SEVERITY,
        help="how bad it is (default: {0}) — raise it deliberately, with the reason "
             "visible in the symptom".format(DEFAULT_SEVERITY),
    )
    p.add_argument("--repro", default="", help="steps to reproduce; required for a bug")
    p.add_argument(
        "--contract",
        default="",
        help="the plugin's own stated contract the behavior contradicts; required for a bug",
    )
    p.add_argument(
        "--limitation",
        default="",
        help="the limitation actually hit; required for a feature request",
    )
    p.add_argument("--workaround", default="", help="what you did instead")
    p.add_argument("--fix", default="", help="optional suggested fix")
    p.add_argument("--label", default="", help="override the per-kind label")
    p.add_argument(
        ALLOW_UNLISTED,
        action="store_true",
        help="file anyway when --plugin is not in this marketplace's manifest; a plugin "
             "from elsewhere belongs in its own project's tracker, so use this only when "
             "the manifest is the thing that is stale",
    )
    p.add_argument(
        "--draft",
        action="store_true",
        help="print the report and file nothing (the worker-tier path for a feature request)",
    )
    return p


def _validate(args):
    """Kind-dependent requirements, reported as usage errors rather than a bad issue."""
    problems = []
    if args.kind == KIND_BUG:
        if not args.contract.strip():
            problems.append(
                "--contract is required for a bug: name the plugin's own stated contract "
                "that the observed behavior contradicts"
            )
        if not args.repro.strip():
            problems.append("--repro is required for a bug: state how to reproduce it")
    else:
        if not args.limitation.strip():
            problems.append(
                "--limitation is required for a feature request: name the limitation you "
                "actually hit, not a nice-to-have"
            )
    return problems


def _default_project(env):
    base = env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.basename(os.path.abspath(base))


def main(argv=None, env=None, runner=None, today=None, out=None):
    env = os.environ if env is None else env
    out = sys.stdout if out is None else out
    runner = subprocess.run if runner is None else runner

    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)

    problems = _validate(args)
    if problems:
        for problem in problems:
            out.write("report_issue: {0}\n".format(problem))
        return 2

    date = args.date.strip() or (today or datetime.date.today().isoformat())
    report = Report(
        kind=args.kind,
        plugin=args.plugin,
        plugin_version=args.plugin_version,
        project=args.project or _default_project(env),
        date=date,
        severity=args.severity,
        summary=args.summary,
        symptom=args.symptom,
        repro=args.repro,
        contract=args.contract,
        limitation=args.limitation,
        workaround=args.workaround,
        fix=args.fix,
    )

    title = build_title(report)
    body = build_body(report)
    label = resolve_label(report.kind, env, args.label.strip() or None)
    repo = resolve_repo(env)

    # Before the draft branch on purpose: a draft is a read of the same boundary, and a
    # dispatcher handed a misdirected draft is the reader this is here to stop.
    allowed, listed = membership(report.plugin.strip(), env, repo, runner)
    if listed is None:
        out.write(
            "report_issue: cannot read this marketplace's plugin list — filing without "
            "the membership check.\n"
        )
    elif not allowed and not args.allow_unlisted:
        out.write(membership_refusal(report.plugin.strip(), listed))
        return 2

    if args.draft:
        out.write(render_draft(report, title, body, label, describe_target(repo, env)))
        return 0

    if not repo:
        out.write(
            "report_issue: cannot tell which repo to file against. Set {0} to owner/name, "
            "or give the plugin manifest a `repository`. Rerun with --draft to print the "
            "report instead.\n".format(REPO_ENV)
        )
        return 2

    # Announced before the call, not after: an agent or a human watching the transcript
    # gets to see the destination while it can still stop a misdirected report.
    out.write(
        "report_issue: filing to {0} — {1}.\n".format(
            describe_target(repo, env), SCOPE_NOTE
        )
    )
    live = live_labels(repo, runner)
    if label and live and label not in live:
        out.write(unlabelled_notice(label, repo, report.kind))
        label = None

    try:
        done = _run_gh(build_argv(repo, title, body, label), runner)
        stdout = getattr(done, "stdout", "") or ""
        stderr = getattr(done, "stderr", "") or ""
        if getattr(done, "returncode", 1) != 0 and LABEL_MISSING.search(stderr):
            # The label is the least important part of the report and the only part that
            # can fail on its own. Retry unlabelled rather than hand back a composed body
            # the filer would have to reconstruct.
            out.write(unlabelled_notice(label, repo, report.kind))
            done = _run_gh(build_argv(repo, title, body, None), runner)
            stdout = getattr(done, "stdout", "") or ""
            stderr = getattr(done, "stderr", "") or ""
    except GhUnavailable:
        # Same class as an unresolvable target repo, and reported the same way: a
        # precondition the caller fixes and reruns, caught before anything left the
        # machine — never confused with `gh ran and the call failed` below.
        out.write(GH_MISSING)
        return 2
    if getattr(done, "returncode", 1) != 0:
        out.write("report_issue: gh issue create failed.\n{0}{1}".format(stdout, stderr))
        return 1
    out.write(stdout if stdout.endswith("\n") else stdout + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
