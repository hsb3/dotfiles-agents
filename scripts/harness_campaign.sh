#!/usr/bin/env bash
# Weekly agent-harness campaign runner + its launchd lifecycle.
#
# Runs the full eval grid over every *cased* candidate:
#     cased candidates  x  {claude, opencode}  x  {with, baseline}  x  3 trials
# model pinned to claude-sonnet-4-5. Candidates are the harness/cases/*/ basenames
# minus _template (scaffold) and smoke-echo (no primitives-core source).
#
# Subcommands (default: run):
#   run        execute the campaign now (what the launchd agent invokes)
#   install    render + bootstrap the weekly user LaunchAgent (Mon 09:00 local)
#   uninstall  bootout + remove the installed LaunchAgent plist
#   status     summarize launchctl state (state / last exit / next fire)
#
# NEVER INGESTS INTO POCKETBASE. This runner only appends to the harness ledger
# (harness/results.jsonl) + per-run logs. It must not touch evals/pb_data/data.db:
# that file is TRACKED, and an unattended write would dirty the working tree outside
# the stop-server -> checkpoint -> commit-with-cause discipline. Ingesting a campaign
# into extender-db is a deliberate, in-session action via evals/load_harness_runs.py
# (see evals/PROCEDURES.md -> "ingesting a harness campaign").
#
# Resume semantics: CAMPAIGN defaults to weekly-YYYYMMDD, and that label is the first
# segment of the harness resume key (campaign|harness|model|candidate|case|config|trial).
# A same-day re-invocation therefore RESUMES — already-completed cells are skipped, only
# missing/failed cells re-run. Override with CAMPAIGN=<label> to force a fresh grid.
#
# Test seam: HARNESS_CAMPAIGN_DRYRUN=1 makes the per-candidate + per-report steps PRINT
# the exact command they would run (after full candidate resolution, including flat-agent
# staging) instead of executing agent-harness. Everything else (preconditions, key fetch,
# discovery, dir resolution) runs for real, so it is a genuine structural check.
#
# launchd note: launchd hands the agent a bare PATH, so `run` prepends the locations of
# `secret` (~/.local/bin) and the brew CLIs (/opt/homebrew/bin) before anything else.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.hsb3.dotfiles-agents.harness-campaign"

# --- staged flat-agent temp dirs, cleaned on any exit ---
STAGED_DIRS=()
cleanup() {
  if [ "${#STAGED_DIRS[@]}" -gt 0 ]; then
    local d
    for d in "${STAGED_DIRS[@]}"; do
      rm -rf "$d"
    done
  fi
}
trap cleanup EXIT

# --------------------------------------------------------------------------------------
cmd_run() {
  # launchd gives a bare PATH; secret lives in ~/.local/bin, brew tools in /opt/homebrew/bin.
  export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  cd "$REPO"

  # Preconditions: every live CLI this campaign needs must be on PATH.
  local missing=""
  local tool
  for tool in claude opencode uv secret; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
  done
  if [ -n "$missing" ]; then
    echo "error: required tool(s) not on PATH:$missing" >&2
    exit 1
  fi

  # Headless auth: both CLIs read ANTHROPIC_API_KEY (keychain via the `secret` CLI).
  ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY 2>/dev/null || true)"
  export ANTHROPIC_API_KEY
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "error: ANTHROPIC_API_KEY is empty (secret get returned nothing)" >&2
    exit 1
  fi

  local campaign="${CAMPAIGN:-weekly-$(date +%Y%m%d)}"
  local dryrun="${HARNESS_CAMPAIGN_DRYRUN:-0}"
  local logdir="harness/campaign-logs"
  mkdir -p "$logdir"
  local log="$logdir/$campaign.log"
  # Dryrun must never pollute the real campaign log (a stray tee'd "complete" line
  # misleads anything tailing the log for the live run's state).
  if [ "$dryrun" = "1" ]; then log="/dev/null"; fi

  echo "=== harness campaign '$campaign' @ $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$log"

  # Discover candidates: harness/cases/*/ basenames minus _template + smoke-echo.
  # Plain glob loop (glob order is already sorted) — no process substitution: bash 3.2
  # (what launchd's bare PATH resolves for the shebang) can't parse an unparenthesized
  # case pattern inside <(...), and the launchd path must run on 3.2.
  local candidates=()
  local name n d
  for d in harness/cases/*/; do
    n="${d%/}"; n="${n##*/}"
    case "$n" in (_template|smoke-echo) continue ;; esac
    candidates+=("$n")
  done
  if [ "${#candidates[@]}" -eq 0 ]; then
    echo "error: no candidates discovered under harness/cases/" | tee -a "$log" >&2
    exit 1
  fi
  echo "candidates: ${candidates[*]}" | tee -a "$log"

  local failures=0
  local dir stage st

  # --- eval each candidate; a failure records + continues, never aborts the grid ---
  for name in "${candidates[@]}"; do
    # Resolve --candidate-dir exactly like the harness-eval Makefile recipe:
    # a skill dir under primitives-core, else a flat agents/<name>.md staged into a tempdir.
    dir="$(find primitives-core -mindepth 2 -maxdepth 2 -type d -name "$name" | head -1)"
    stage=""
    if [ -z "$dir" ] && [ -f "primitives-core/agents/$name.md" ]; then
      stage="$(mktemp -d)"
      STAGED_DIRS+=("$stage")
      cp "primitives-core/agents/$name.md" "$stage/"
      dir="$stage"
      echo "staged agent candidate '$name' from primitives-core/agents/$name.md -> $dir" | tee -a "$log"
    fi
    if [ -z "$dir" ]; then
      echo "WARN: no primitive named '$name' (need a skill dir or agents/$name.md); marking failure" | tee -a "$log"
      failures=$((failures + 1))
      continue
    fi

    if [ "$dryrun" = "1" ]; then
      echo "DRYRUN: uv run --project harness agent-harness $name --candidate-dir $dir --harness claude,opencode --model claude-sonnet-4-5 --configs with,baseline --trials 3 --campaign $campaign"
      continue
    fi

    set +e
    uv run --project harness agent-harness "$name" \
      --candidate-dir "$dir" \
      --harness claude,opencode \
      --model claude-sonnet-4-5 \
      --configs with,baseline \
      --trials 3 \
      --campaign "$campaign" 2>&1 | tee -a "$log"
    st=${PIPESTATUS[0]}
    set -e
    if [ "$st" -ne 0 ]; then
      echo "FAILED: candidate '$name' exited $st" | tee -a "$log"
      failures=$((failures + 1))
    fi
  done

  # --- aggregate the ledger per candidate ---
  for name in "${candidates[@]}"; do
    if [ "$dryrun" = "1" ]; then
      echo "DRYRUN: uv run --project harness agent-harness $name --report"
      continue
    fi
    echo "=== report: $name ===" | tee -a "$log"
    set +e
    uv run --project harness agent-harness "$name" --report 2>&1 | tee -a "$log"
    set -e
  done

  local status_word
  if [ "$failures" -eq 0 ]; then status_word="ok"; else status_word="$failures failed"; fi
  echo "campaign '$campaign' complete: $status_word (log: $log)" | tee -a "$log"

  if [ "$dryrun" != "1" ]; then
    osascript -e "display notification \"$campaign: $status_word\" with title \"harness campaign\"" >/dev/null 2>&1 || true
  fi

  [ "$failures" -eq 0 ] || exit 1
}

# --------------------------------------------------------------------------------------
cmd_install() {
  local tmpl="$REPO/scripts/launchd/$LABEL.plist.template"
  local dest="$HOME/Library/LaunchAgents/$LABEL.plist"
  [ -f "$tmpl" ] || { echo "error: template not found: $tmpl" >&2; exit 1; }

  mkdir -p "$HOME/Library/LaunchAgents"
  local rendered
  rendered="$(mktemp)"
  sed -e "s|@REPO@|$REPO|g" -e "s|@HOME@|$HOME|g" "$tmpl" > "$rendered"
  mv "$rendered" "$dest"

  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$dest"
  echo "installed: $dest"
  echo "next: run once now to approve any Keychain prompt while logged in:"
  echo "  launchctl kickstart -k gui/$UID/$LABEL"
}

# --------------------------------------------------------------------------------------
cmd_uninstall() {
  local dest="$HOME/Library/LaunchAgents/$LABEL.plist"
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  rm -f "$dest"
  echo "uninstalled: $LABEL"
}

# --------------------------------------------------------------------------------------
cmd_status() {
  local target="gui/$UID/$LABEL"
  local out
  if out="$(launchctl print "$target" 2>/dev/null)"; then
    echo "agent loaded: $target"
    printf '%s\n' "$out" \
      | grep -iE 'state =|last exit|runatload|calendarinterval|nextfiredate|next fire' \
      || echo "  (loaded; no summary lines matched — run: launchctl print $target)"
  else
    echo "agent not loaded ($LABEL). Install with: scripts/harness_campaign.sh install"
  fi
}

# --------------------------------------------------------------------------------------
main() {
  local sub="${1:-run}"
  case "$sub" in
    run)       cmd_run ;;
    install)   cmd_install ;;
    uninstall) cmd_uninstall ;;
    status)    cmd_status ;;
    *) echo "usage: $(basename "$0") [run|install|uninstall|status]" >&2; exit 2 ;;
  esac
}

main "$@"
