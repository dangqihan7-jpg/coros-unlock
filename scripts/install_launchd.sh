#!/usr/bin/env bash
# Convenience wrapper: generate and load the launchd agent.
set -euo pipefail

PLIST="$HOME/Library/LaunchAgents/com.corosunlock.daemon.plist"

if ! command -v coros-unlock >/dev/null 2>&1; then
  echo "coros-unlock is not on PATH. Install with: pip install -e ." >&2
  exit 1
fi

coros-unlock install
mkdir -p "$HOME/Library/Logs"

if launchctl print "gui/$(id -u)/com.corosunlock.daemon" >/dev/null 2>&1; then
  launchctl bootout "gui/$(id -u)/com.corosunlock.daemon" || true
fi
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Loaded. Follow logs with: tail -f ~/Library/Logs/coros-unlock.log"
