#!/bin/bash
# Obsidian CLI - Daily Note Automation Examples
# Demonstrates common daily note workflows and automation patterns

set -e  # Exit on error

# Configuration
OBSIDIAN="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
VAULT="MyVault"  # Change to your vault name

# Helper function
run_obsidian() {
  $OBSIDIAN vault="$VAULT" "$@"
}

# ============================================================================
# Example 1: Morning Standup Template
# ============================================================================

morning_standup() {
  echo "Adding morning standup to daily note..."

  local standup=$(cat <<EOF

## Morning Standup - $(date '+%H:%M')

### 🎯 Today's Goals
-

### 📅 Scheduled
-

### 🔥 Priorities
1.
2.
3.

---
EOF
)

  run_obsidian daily:append content="$standup"
  echo "✓ Standup added to daily note"
}

# ============================================================================
# Example 2: Evening Review
# ============================================================================

evening_review() {
  echo "Adding evening review to daily note..."

  local review=$(cat <<EOF

## Evening Review - $(date '+%H:%M')

### ✅ Completed
-

### 🚧 In Progress
-

### 📝 Notes
-

### 💡 Learnings
-

---
EOF
)

  run_obsidian daily:append content="$review"
  echo "✓ Review template added"
}

# ============================================================================
# Example 3: Quick Capture to Daily Note
# ============================================================================

quick_capture() {
  local note="${1:-Quick note}"
  local timestamp=$(date '+%H:%M')

  run_obsidian daily:append content="- [$timestamp] $note" inline
  echo "✓ Captured: $note"
}

# ============================================================================
# Example 4: Time-Stamped Log Entry
# ============================================================================

log_entry() {
  local message="$1"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  run_obsidian daily:append content="[$timestamp] $message"
  echo "✓ Logged: $message"
}

# ============================================================================
# Example 5: Meeting Notes
# ============================================================================

meeting_notes() {
  local title="${1:-Team Meeting}"
  local participants="${2:-Team}"

  local notes=$(cat <<EOF

## $title - $(date '+%H:%M')

**Participants:** $participants
**Date:** $(date '+%Y-%m-%d')

### Agenda


### Discussion


### Action Items
- [ ]

### Decisions


---
EOF
)

  run_obsidian daily:append content="$notes"
  echo "✓ Meeting notes template added"
}

# ============================================================================
# Example 6: Pomodoro Session Tracker
# ============================================================================

pomodoro_start() {
  local task="${1:-Work session}"
  local timestamp=$(date '+%H:%M')

  run_obsidian daily:append content="🍅 [$timestamp] Started: $task"
  echo "✓ Pomodoro started for: $task"

  # Store start time for later
  echo "$timestamp|$task" > /tmp/obsidian-pomodoro.tmp
}

pomodoro_complete() {
  if [ ! -f /tmp/obsidian-pomodoro.tmp ]; then
    echo "❌ No active pomodoro session"
    return 1
  fi

  local start_time=$(cat /tmp/obsidian-pomodoro.tmp | cut -d'|' -f1)
  local task=$(cat /tmp/obsidian-pomodoro.tmp | cut -d'|' -f2)
  local end_time=$(date '+%H:%M')

  run_obsidian daily:append content="   ✓ [$end_time] Completed: $task"
  echo "✓ Pomodoro completed"

  rm /tmp/obsidian-pomodoro.tmp
}

# ============================================================================
# Example 7: Daily Weather & Context
# ============================================================================

add_daily_context() {
  echo "Adding daily context..."

  # Get weather (requires wttr.in or similar API)
  local weather=$(curl -s "wttr.in/?format=%C+%t" 2>/dev/null || echo "Weather unavailable")

  local context=$(cat <<EOF

## Daily Context - $(date '+%A, %B %d, %Y')

**Weather:** $weather
**Week:** Week $(date '+%U')
**Day of Year:** $(date '+%j')/365

---
EOF
)

  run_obsidian daily:prepend content="$context"
  echo "✓ Daily context added"
}

# ============================================================================
# Example 8: Habit Tracker
# ============================================================================

habit_tracker() {
  echo "Adding habit tracker..."

  local habits=$(cat <<EOF

## Habits - $(date '+%Y-%m-%d')

- [ ] Morning exercise
- [ ] Meditation (10 min)
- [ ] Reading (30 min)
- [ ] Journal
- [ ] No phone before 9am
- [ ] Bed by 11pm

---
EOF
)

  run_obsidian daily:append content="$habits"
  echo "✓ Habit tracker added"
}

# ============================================================================
# Example 9: Link Yesterday's Note
# ============================================================================

link_yesterday() {
  local yesterday=$(date -v-1d '+%Y-%m-%d')

  run_obsidian daily:prepend content="← [[${yesterday}]] | → "
  echo "✓ Linked to yesterday's note"
}

# ============================================================================
# Example 10: Daily Note Automation Workflow
# ============================================================================

daily_workflow() {
  echo "==================================="
  echo "Daily Note Automation Workflow"
  echo "==================================="

  # Check if daily note exists, create if not
  if ! run_obsidian daily:read &>/dev/null; then
    echo "Creating new daily note..."
    run_obsidian daily silent
  fi

  # Run morning routine
  echo ""
  echo "Morning routine:"
  add_daily_context
  link_yesterday
  habit_tracker
  morning_standup

  echo ""
  echo "✓ Daily note setup complete!"
  echo ""
  echo "To open daily note in Obsidian:"
  echo "  $OBSIDIAN vault=\"$VAULT\" daily"
}

# ============================================================================
# Example 11: Extract Tasks from Daily Note
# ============================================================================

extract_tasks() {
  echo "Extracting tasks from daily note..."

  local content=$(run_obsidian daily:read)

  echo ""
  echo "## Tasks:"
  echo "$content" | grep -E '^\s*- \[[ x]\]' || echo "No tasks found"

  echo ""
  echo "## Incomplete:"
  echo "$content" | grep -E '^\s*- \[ \]' || echo "All tasks complete!"
}

# ============================================================================
# Example 12: Append External Data
# ============================================================================

append_github_activity() {
  echo "Fetching GitHub activity..."

  # Replace with your GitHub username
  local username="${GITHUB_USER:-your-username}"

  # Get recent commits (requires gh CLI)
  if command -v gh &> /dev/null; then
    local activity=$(gh api "users/$username/events/public" --jq '.[0:3] | .[] | "- \(.type): \(.repo.name)"')

    run_obsidian daily:append content="## GitHub Activity
$activity

---"
    echo "✓ GitHub activity appended"
  else
    echo "❌ GitHub CLI not installed"
  fi
}

# ============================================================================
# Example 13: Archive Old Daily Notes
# ============================================================================

archive_old_dailies() {
  local days_old="${1:-30}"
  local cutoff=$(date -v-${days_old}d '+%Y-%m-%d')

  echo "Archiving daily notes older than $cutoff..."

  # Find files matching YYYY-MM-DD pattern
  run_obsidian files folder=daily | grep -E '[0-9]{4}-[0-9]{2}-[0-9]{2}' | while read -r line; do
    local filename=$(echo "$line" | sed 's/^- //')
    local date_part=$(echo "$filename" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')

    if [[ "$date_part" < "$cutoff" ]]; then
      echo "  Archiving: $filename"
      run_obsidian move path="daily/$filename" to="archive/daily/$filename"
    fi
  done

  echo "✓ Archive complete"
}

# ============================================================================
# Main Script
# ============================================================================

case "${1:-}" in
  standup)
    morning_standup
    ;;
  review)
    evening_review
    ;;
  capture)
    quick_capture "${2:-Quick note}"
    ;;
  log)
    log_entry "$2"
    ;;
  meeting)
    meeting_notes "${2:-Meeting}" "${3:-Team}"
    ;;
  pomodoro-start)
    pomodoro_start "${2:-Work session}"
    ;;
  pomodoro-done)
    pomodoro_complete
    ;;
  context)
    add_daily_context
    ;;
  habits)
    habit_tracker
    ;;
  link-yesterday)
    link_yesterday
    ;;
  workflow)
    daily_workflow
    ;;
  tasks)
    extract_tasks
    ;;
  github)
    append_github_activity
    ;;
  archive)
    archive_old_dailies "${2:-30}"
    ;;
  *)
    echo "Obsidian CLI - Daily Note Automation"
    echo ""
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  standup              Add morning standup template"
    echo "  review               Add evening review template"
    echo "  capture [text]       Quick capture to daily note"
    echo "  log <message>        Add timestamped log entry"
    echo "  meeting [title]      Add meeting notes template"
    echo "  pomodoro-start [task] Start pomodoro session"
    echo "  pomodoro-done        Complete pomodoro session"
    echo "  context              Add daily context (weather, date)"
    echo "  habits               Add habit tracker"
    echo "  link-yesterday       Link to previous daily note"
    echo "  workflow             Run full morning workflow"
    echo "  tasks                Extract tasks from daily note"
    echo "  github               Append GitHub activity"
    echo "  archive [days]       Archive old daily notes (default: 30 days)"
    echo ""
    echo "Examples:"
    echo "  $0 workflow          # Run morning setup"
    echo "  $0 capture 'Meeting with John at 2pm'"
    echo "  $0 pomodoro-start 'Write documentation'"
    echo "  $0 archive 60        # Archive notes older than 60 days"
    exit 1
    ;;
esac
