#!/bin/bash
# Obsidian CLI - Vault Report Generation Examples
# Generate comprehensive reports and analytics from your Obsidian vault

set -e

# Configuration
OBSIDIAN="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
VAULT="MyVault"  # Change to your vault name

# Helper function
run_obsidian() {
  $OBSIDIAN vault="$VAULT" "$@"
}

# ============================================================================
# Example 1: Basic Vault Statistics
# ============================================================================

vault_stats() {
  local output="vault-stats-$(date +%Y-%m-%d).md"

  cat > "$output" <<EOF
# Vault Statistics
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Overview

- **Vault Name:** $(run_obsidian vault info=name)
- **Total Files:** $(run_obsidian files total)
- **Total Folders:** $(run_obsidian folders total)
- **Markdown Files:** $(run_obsidian files ext=md total)

## Link Health

- **Orphaned Files:** $(run_obsidian orphans total)
- **Dead-End Files:** $(run_obsidian deadends total)
- **Unresolved Links:** $(run_obsidian unresolved total)

## Content

- **Total Tags:** $(run_obsidian tags total)
- **Total Properties:** $(run_obsidian properties total)
- **Total Tasks:** $(run_obsidian tasks all total)
- **Incomplete Tasks:** $(run_obsidian tasks todo total)

EOF

  echo "✓ Vault statistics saved to: $output"
  cat "$output"
}

# ============================================================================
# Example 2: Tag Usage Report
# ============================================================================

tag_report() {
  local output="tag-report-$(date +%Y-%m-%d).md"

  echo "Generating tag usage report..."

  cat > "$output" <<EOF
# Tag Usage Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Tag Statistics

Total tags: $(run_obsidian tags total)

## Top Tags

EOF

  # Get tags with counts (requires JSON format)
  run_obsidian tags counts format=json 2>/dev/null | \
    jq -r '.[] | "\(.count)\t#\(.tag)"' | \
    sort -rn | \
    head -20 | \
    awk '{print "- **" $2 "** (" $1 " uses)"}' >> "$output"

  echo ""  >> "$output"
  echo "## All Tags" >> "$output"
  echo "" >> "$output"

  run_obsidian tags | sed 's/^/- /' >> "$output"

  echo "✓ Tag report saved to: $output"
}

# ============================================================================
# Example 3: Link Analysis Report
# ============================================================================

link_analysis() {
  local output="link-analysis-$(date +%Y-%m-%d).md"

  echo "Analyzing vault links..."

  cat > "$output" <<EOF
# Link Analysis Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Orphaned Files (No Incoming Links)

Total: $(run_obsidian orphans total)

EOF

  run_obsidian orphans | sed 's/^/- /' >> "$output"

  cat >> "$output" <<EOF

## Dead-End Files (No Outgoing Links)

Total: $(run_obsidian deadends total)

EOF

  run_obsidian deadends | sed 's/^/- /' >> "$output"

  cat >> "$output" <<EOF

## Unresolved Links

Total: $(run_obsidian unresolved total)

EOF

  run_obsidian unresolved | sed 's/^/- /' >> "$output"

  echo "✓ Link analysis saved to: $output"
}

# ============================================================================
# Example 4: Most Connected Notes (Hub Files)
# ============================================================================

hub_files() {
  local output="hub-files-$(date +%Y-%m-%d).md"

  echo "Finding most connected notes..."

  cat > "$output" <<EOF
# Hub Files Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

Notes with the most connections (incoming + outgoing links).

## Top Hub Files

EOF

  # Create temporary file for processing
  local temp_file=$(mktemp)

  # Get all markdown files
  run_obsidian files ext=md | sed 's/^- //' | while read -r file; do
    # Get backlink count
    local backlinks=$(run_obsidian backlinks file="$file" total 2>/dev/null || echo 0)
    # Get outgoing link count
    local links=$(run_obsidian links file="$file" total 2>/dev/null || echo 0)
    # Calculate total
    local total=$((backlinks + links))

    echo "$total|$backlinks|$links|$file" >> "$temp_file"
  done

  # Sort and format
  sort -t'|' -k1 -rn "$temp_file" | head -20 | while IFS='|' read -r total backlinks links file; do
    echo "- **$file** (Total: $total, In: $backlinks, Out: $links)" >> "$output"
  done

  rm "$temp_file"

  echo "✓ Hub files report saved to: $output"
}

# ============================================================================
# Example 5: Task Overview Report
# ============================================================================

task_overview() {
  local output="task-overview-$(date +%Y-%m-%d).md"

  echo "Generating task overview..."

  cat > "$output" <<EOF
# Task Overview Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Summary

- **Total Tasks:** $(run_obsidian tasks all total)
- **Incomplete:** $(run_obsidian tasks todo total)
- **Completed:** $(run_obsidian tasks done total)

## Incomplete Tasks by File

EOF

  # Get files with incomplete tasks
  run_obsidian tasks todo format=json 2>/dev/null | \
    jq -r '.[] | .file' | \
    sort | uniq -c | \
    sort -rn | \
    awk '{print "- **" $2 "** (" $1 " tasks)"}' >> "$output"

  cat >> "$output" <<EOF

## All Incomplete Tasks

EOF

  run_obsidian tasks todo verbose >> "$output"

  echo "✓ Task overview saved to: $output"
}

# ============================================================================
# Example 6: Property Usage Report
# ============================================================================

property_report() {
  local output="property-report-$(date +%Y-%m-%d).md"

  echo "Analyzing property usage..."

  cat > "$output" <<EOF
# Property Usage Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Property Statistics

Total unique properties: $(run_obsidian properties total)

## Properties by Usage

EOF

  run_obsidian properties counts sort=count format=tsv 2>/dev/null | \
    awk -F'\t' '{print "- **" $1 "** (" $2 " files)"}' >> "$output"

  echo "✓ Property report saved to: $output"
}

# ============================================================================
# Example 7: Recent Activity Report
# ============================================================================

recent_activity() {
  local output="recent-activity-$(date +%Y-%m-%d).md"

  echo "Generating recent activity report..."

  cat > "$output" <<EOF
# Recent Activity Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Recently Opened Files

EOF

  run_obsidian recents | sed 's/^/- /' >> "$output"

  echo "✓ Recent activity saved to: $output"
}

# ============================================================================
# Example 8: Folder Structure Report
# ============================================================================

folder_structure() {
  local output="folder-structure-$(date +%Y-%m-%d).md"

  echo "Analyzing folder structure..."

  cat > "$output" <<EOF
# Folder Structure Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Folder Statistics

Total folders: $(run_obsidian folders total)

## Folders by File Count

EOF

  run_obsidian folders | sed 's/^- //' | while read -r folder; do
    local file_count=$(run_obsidian files folder="$folder" total 2>/dev/null || echo 0)
    echo "$file_count|$folder"
  done | sort -t'|' -k1 -rn | while IFS='|' read -r count folder; do
    echo "- **$folder/** ($count files)" >> "$output"
  done

  echo "✓ Folder structure saved to: $output"
}

# ============================================================================
# Example 9: Plugin Usage Report
# ============================================================================

plugin_report() {
  local output="plugin-report-$(date +%Y-%m-%d).md"

  echo "Generating plugin report..."

  cat > "$output" <<EOF
# Plugin Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Enabled Community Plugins

EOF

  run_obsidian plugins:enabled filter=community | sed 's/^/- /' >> "$output"

  cat >> "$output" <<EOF

## Enabled Core Plugins

EOF

  run_obsidian plugins:enabled filter=core | sed 's/^/- /' >> "$output"

  echo "✓ Plugin report saved to: $output"
}

# ============================================================================
# Example 10: Comprehensive Vault Health Report
# ============================================================================

health_report() {
  local output="vault-health-$(date +%Y-%m-%d).md"

  echo "Generating comprehensive vault health report..."

  cat > "$output" <<EOF
# Vault Health Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Executive Summary

- **Vault:** $(run_obsidian vault info=name)
- **Total Files:** $(run_obsidian files total)
- **Health Score:**
EOF

  # Calculate health score (simple example)
  local total_files=$(run_obsidian files ext=md total)
  local orphans=$(run_obsidian orphans total)
  local unresolved=$(run_obsidian unresolved total)

  local orphan_pct=$(awk "BEGIN {printf \"%.1f\", ($orphans / $total_files) * 100}")
  local health_score=$(awk "BEGIN {printf \"%.0f\", 100 - $orphan_pct}")

  echo "  - **Overall:** $health_score/100" >> "$output"
  echo "  - **Orphaned Rate:** $orphan_pct%" >> "$output"

  cat >> "$output" <<EOF

## Detailed Analysis

### Files
- Total: $total_files
- Orphaned: $orphans ($orphan_pct%)
- Dead-ends: $(run_obsidian deadends total)

### Links
- Unresolved: $unresolved
- Internal links working: $(awk "BEGIN {printf \"%.1f\", 100 - (($unresolved / ($total_files * 10)) * 100)}")%

### Content
- Total tags: $(run_obsidian tags total)
- Total tasks: $(run_obsidian tasks all total)
- Incomplete tasks: $(run_obsidian tasks todo total)

### Organization
- Folders: $(run_obsidian folders total)
- Properties used: $(run_obsidian properties total)

## Recommendations

EOF

  # Add recommendations based on analysis
  if [ "$orphans" -gt 0 ]; then
    echo "- ⚠️  **$orphans orphaned files** - Consider linking or archiving" >> "$output"
  fi

  if [ "$unresolved" -gt 0 ]; then
    echo "- ⚠️  **$unresolved unresolved links** - Fix broken links" >> "$output"
  fi

  local deadends=$(run_obsidian deadends total)
  if [ "$deadends" -gt 10 ]; then
    echo "- ⚠️  **$deadends dead-end files** - Add outgoing links for better connectivity" >> "$output"
  fi

  if [ "$health_score" -ge 80 ]; then
    echo "- ✅ **Vault health is good!** Keep up the maintenance." >> "$output"
  fi

  echo ""  >> "$output"
  echo "---" >> "$output"
  echo "" >> "$output"
  echo "*Report generated with Obsidian CLI*" >> "$output"

  echo "✓ Comprehensive health report saved to: $output"
}

# ============================================================================
# Example 11: Generate All Reports
# ============================================================================

generate_all() {
  local report_dir="reports-$(date +%Y-%m-%d)"
  mkdir -p "$report_dir"

  echo "Generating all vault reports in: $report_dir"
  echo ""

  cd "$report_dir"

  vault_stats
  echo ""
  tag_report
  echo ""
  link_analysis
  echo ""
  task_overview
  echo ""
  property_report
  echo ""
  recent_activity
  echo ""
  folder_structure
  echo ""
  plugin_report
  echo ""
  health_report

  cd ..

  echo ""
  echo "======================================"
  echo "✓ All reports generated successfully!"
  echo "======================================"
  echo "Location: $report_dir/"
  echo ""
}

# ============================================================================
# Main Script
# ============================================================================

case "${1:-}" in
  stats)
    vault_stats
    ;;
  tags)
    tag_report
    ;;
  links)
    link_analysis
    ;;
  hubs)
    hub_files
    ;;
  tasks)
    task_overview
    ;;
  properties)
    property_report
    ;;
  recent)
    recent_activity
    ;;
  folders)
    folder_structure
    ;;
  plugins)
    plugin_report
    ;;
  health)
    health_report
    ;;
  all)
    generate_all
    ;;
  *)
    echo "Obsidian CLI - Vault Report Generation"
    echo ""
    echo "Usage: $0 <report-type>"
    echo ""
    echo "Report Types:"
    echo "  stats        Basic vault statistics"
    echo "  tags         Tag usage analysis"
    echo "  links        Link health (orphans, dead-ends, unresolved)"
    echo "  hubs         Most connected notes"
    echo "  tasks        Task overview and breakdown"
    echo "  properties   Property usage statistics"
    echo "  recent       Recent activity"
    echo "  folders      Folder structure analysis"
    echo "  plugins      Plugin usage"
    echo "  health       Comprehensive vault health report"
    echo "  all          Generate all reports"
    echo ""
    echo "Examples:"
    echo "  $0 health    # Generate health report"
    echo "  $0 all       # Generate all reports in subdirectory"
    exit 1
    ;;
esac
