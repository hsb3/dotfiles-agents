#!/bin/sh
# Schedules the agent-harness weekly campaign with launchd (macOS).
#
#   launchd.sh install <cases-dir> <candidates-root>   write and load the LaunchAgent (Mondays 09:00)
#   launchd.sh uninstall                               unload it and delete the plist
#   launchd.sh status                                  state, last exit and next fire, or "agent not loaded"
#   launchd.sh run <cases-dir> <candidates-root>       what launchd runs: the campaign, then a notification
set -u

LABEL=com.hsb3.agent-harness.campaign
PKG=$(cd "$(dirname "$0")/.." && pwd)
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

usage() {
  echo "usage: $0 install <cases-dir> <candidates-root> | uninstall | status | run <cases-dir> <candidates-root>" >&2
  exit 2
}

# Absolute path of an existing directory.
absdir() {
  (cd "$1" 2>/dev/null && pwd) || {
    echo "$0: no such directory: $1" >&2
    exit 2
  }
}

xml() {
  printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

write_plist() {
  mkdir -p "$(dirname "$PLIST")" "$HOME/Library/Logs"
  cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>$(xml "$PKG/scripts/launchd.sh")</string>
    <string>run</string>
    <string>$(xml "$1")</string>
    <string>$(xml "$2")</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$(xml "$PKG")</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key>
    <integer>1</integer>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>$(xml "$HOME/Library/Logs/agent-harness-campaign.out.log")</string>
  <key>StandardErrorPath</key>
  <string>$(xml "$HOME/Library/Logs/agent-harness-campaign.err.log")</string>
</dict>
</plist>
EOF
}

cmd_install() {
  [ $# -eq 2 ] || usage
  cases=$(absdir "$1") || exit 2
  root=$(absdir "$2") || exit 2
  write_plist "$cases" "$root"
  launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
  launchctl bootstrap "$DOMAIN" "$PLIST" || exit 1
  echo "installed $PLIST"
  echo "next: launchctl kickstart -k $DOMAIN/$LABEL   (runs it once now and approves any keychain prompt)"
}

cmd_uninstall() {
  launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  echo "uninstalled $LABEL"
}

cmd_status() {
  if out=$(launchctl print "$DOMAIN/$LABEL" 2>/dev/null); then
    printf '%s\n' "$out" | grep -E '^[[:space:]]*(state|last exit|next fire)' | sed -e 's/^[[:space:]]*//'
  else
    echo "agent not loaded"
  fi
}

cmd_run() {
  [ $# -eq 2 ] || usage
  PATH="$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
  export PATH
  if command -v secret >/dev/null 2>&1; then
    for name in ANTHROPIC_API_KEY OPENAI_API_KEY; do
      eval "current=\${$name:-}"
      if [ -z "$current" ]; then
        # The value goes straight into the environment; it is never printed.
        if value=$(secret get "$name" 2>/dev/null) && [ -n "$value" ]; then
          eval "$name=\$value"
          export "$name"
        fi
      fi
    done
    unset current value
  fi
  bun "$PKG/src/cli.ts" campaign --cases-dir "$1" --candidates-root "$2"
  code=$?
  if [ "$code" -eq 0 ]; then message="agent-harness campaign: ok"; else message="agent-harness campaign: failed"; fi
  osascript -e "display notification \"$message\" with title \"agent-harness\"" >/dev/null 2>&1 || true
  exit "$code"
}

[ $# -ge 1 ] || usage
sub=$1
shift
case "$sub" in
  install) cmd_install "$@" ;;
  uninstall) cmd_uninstall ;;
  status) cmd_status ;;
  run) cmd_run "$@" ;;
  *) usage ;;
esac
