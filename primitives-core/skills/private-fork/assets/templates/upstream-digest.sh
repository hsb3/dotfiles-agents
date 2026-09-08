#!/usr/bin/env bash
# upstream-digest.sh — generate a triage digest of upstream commits not yet reviewed.
#
# TEMPLATE from the private-fork skill (proven in the opencode fork). Copy to the
# fork's scripts/ and edit the CONFIG block. Wire a `make upstream-review` target.
#
# Reads the review watermark from $LOG_FILE (line: `Last-reviewed-upstream-commit: <sha>`);
# falls back to the local $MIRROR_BRANCH if the line is missing.
#
# Output: a markdown digest on stdout, pre-categorized — paste-ready for a new session
# block in $LOG_FILE. Also saved under _meta/research/.
#
# Categories (advisory — the review session makes the real call):
#   SKIP   subject matches a known not-applicable pattern
#   FLAG   commit touches a fork-customized / conflict-prone file
#   REVIEW everything else
#
# Above $MAX_DETAIL commits the digest switches to summary mode: FLAG commits get the
# full table, SKIP/REVIEW are histogrammed, and release tags in range are listed so
# verdicts can be recorded at release granularity instead of per commit.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# ── CONFIG — edit per fork ────────────────────────────────────────────────────
LOG_FILE="docs/upstream-review-log.md"   # its Last-reviewed-upstream-commit: must be a SHA; a ref name there re-opens the shadow at the other end of the range
# Full refname, not `upstream/{{BRANCH}}`: `refs/heads/<name>` resolves before
# `refs/remotes/<name>`, so a local ref of that name would shadow the tracking ref.
UPSTREAM_REF="refs/remotes/upstream/{{BRANCH}}"   # e.g. refs/remotes/upstream/main
MIRROR_BRANCH="upstream-{{BRANCH}}"          # local read-only mirror (full tier), a real local branch
UPSTREAM_REPO="{{UPSTREAM_ORG}}/{{NAME}}"    # for PR links
MAX_DETAIL="${MAX_DETAIL:-300}"
# SKIP: commit subjects that are almost never applicable to this fork.
# Keep in sync with the merge SOP's "commit filters" section.
SKIP_RE='^(ci:|release:|chore\(workflows\):|v?[0-9]+\.[0-9]+\.[0-9]+$)'
# FLAG: paths that carry fork customizations (the registry's M- rows).
FLAG_PATHS_RE='({{path/one\.ts}}|{{path/two\.go}}|^package\.json$)'
# ──────────────────────────────────────────────────────────────────────────────

echo "Fetching upstream..." >&2
git fetch upstream --quiet

watermark=""
if [[ -f "$LOG_FILE" ]]; then
  watermark=$(grep -m1 '^Last-reviewed-upstream-commit:' "$LOG_FILE" | awk '{print $2}' || true)
fi
if [[ -z "$watermark" ]]; then
  watermark=$(git rev-parse "$MIRROR_BRANCH")
  echo "No watermark in $LOG_FILE — falling back to $MIRROR_BRANCH ($watermark)" >&2
fi
if ! git cat-file -e "$watermark^{commit}" 2>/dev/null; then
  echo "error: watermark '$watermark' is not a known commit" >&2
  exit 1
fi

head_sha=$(git rev-parse --short "$UPSTREAM_REF")
range="$watermark..$UPSTREAM_REF"
count=$(git rev-list --count "$range")

today=$(date +%Y-%m-%d)
out="_meta/research/upstream-digest-$today.md"
mkdir -p _meta/research

# Single pass: categorize every commit as "<CAT>\t<sha>\t<subject>".
# \x01 marks a commit header line; following lines (until the next header) are its paths.
# Patterns go via the environment: awk -v mangles backslash escapes, ENVIRON does not.
triage=$(git log --reverse --name-only --format=$'\x01%h\t%s' "$range" | SKIP_RE="$SKIP_RE" FLAG_PATHS_RE="$FLAG_PATHS_RE" awk '
  BEGIN { skip = ENVIRON["SKIP_RE"]; flag = ENVIRON["FLAG_PATHS_RE"] }
  function emit() { if (sha != "") print cat "\t" sha "\t" subj }
  /^\x01/ {
    emit()
    line = substr($0, 2)
    tab = index(line, "\t")
    sha = substr(line, 1, tab - 1)
    subj = substr(line, tab + 1)
    cat = (subj ~ skip) ? "SKIP" : "REVIEW"
    next
  }
  cat != "SKIP" && $0 ~ flag { cat = "FLAG" }
  END { emit() }
')

n_skip=$(grep -c $'^SKIP\t' <<<"$triage" || true)
n_flag=$(grep -c $'^FLAG\t' <<<"$triage" || true)
n_review=$(grep -c $'^REVIEW\t' <<<"$triage" || true)

# Render "| _____ | `sha` | subject + PR link | CAT |" rows from triage lines on stdin.
render_rows() {
  while IFS=$'\t' read -r cat sha subject; do
    [[ -z "$sha" ]] && continue
    pr=$(grep -oE '#[0-9]+' <<<"$subject" | head -1 || true)
    link=""
    [[ -n "$pr" ]] && link=" [${pr}](https://github.com/$UPSTREAM_REPO/pull/${pr#\#})"
    subject=${subject//|/\\|}
    echo "| _____ | \`$sha\` | $subject$link | $cat |"
  done
}

{
  echo "### $today — upstream review"
  echo ""
  echo "Range: \`$watermark..$head_sha\` — $count commits (SKIP $n_skip · FLAG $n_flag · REVIEW $n_review)"
  echo ""

  if (( count <= MAX_DETAIL )); then
    echo "| Verdict | Commit | Subject / PR | Auto-triage |"
    echo "|---|---|---|---|"
    render_rows <<<"$triage"
  else
    echo "_${count} commits exceeds detail threshold ($MAX_DETAIL) — summary mode._"
    echo "_Verdict at release granularity; FLAG commits below still get individual eyes._"
    echo ""
    echo "**Release tags in range:**"
    echo ""
    # Tag may sit on an unmerged one-commit release branch — test its merge-base
    # with $UPSTREAM_REF against the watermark instead of ancestry of the tag itself.
    tags=$(git tag -l 'v[0-9]*' --sort=v:refname | while read -r t; do
      b=$(git merge-base "$t" "$UPSTREAM_REF" 2>/dev/null) || continue
      if ! git merge-base --is-ancestor "$b" "$watermark" 2>/dev/null; then
        echo "- $t"
      fi
    done) || true
    if [[ -n "$tags" ]]; then echo "$tags"; else echo "- (none)"; fi
    echo ""
    echo "**FLAG commits (touch fork-customized files):**"
    echo ""
    echo "| Verdict | Commit | Subject / PR | Auto-triage |"
    echo "|---|---|---|---|"
    { grep $'^FLAG\t' <<<"$triage" || true; } | render_rows
    echo ""
    echo "**REVIEW commits by prefix (top 20):**"
    echo ""
    echo '```'
    { grep $'^REVIEW\t' <<<"$triage" || true; } | cut -f3 \
      | sed -E -e 's/^([a-z]+(\([^)]*\))?:).*/\1/' -e 't' -e 's/.*/(no prefix)/' \
      | sort | uniq -c | sort -rn | awk 'NR<=20'
    echo '```'
  fi

  echo ""
  echo "Verdict vocabulary: **adopt** (take via merge/cherry-pick) · **adapt** (take with fork modifications) · **pass** (not applicable) · **defer** (revisit next cycle)."
  echo ""
  echo "After the session: fill the Verdict column, append this block to $LOG_FILE,"
  echo "and advance its \`Last-reviewed-upstream-commit:\` line to \`$head_sha\`."
} | tee "$out"

echo "" >&2
echo "Digest saved to $out" >&2
