#!/usr/bin/env bash
set -euo pipefail
# Heartbeat daemon for Codex CLI agents
# Usage: heartbeat-daemon.sh <team-id> <agent-name>
# Run as background process: heartbeat-daemon.sh team-1 implement &

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"

TEAM_ID="${1:?team-id required}"
AGENT_NAME="${2:?agent-name required}"
INTERVAL="${3:-30}"

TEAM_DIR="$(osc_dir "$(osc_repo_root)")/teams/$TEAM_ID"
HB_FILE="$TEAM_DIR/agents/${AGENT_NAME}.heartbeat"
SHUTDOWN_FILE="$TEAM_DIR/agents/${AGENT_NAME}.shutdown"

while true; do
  # Check shutdown signal
  if [[ -f "$SHUTDOWN_FILE" ]]; then
    echo "shutdown signal detected for $AGENT_NAME, exiting heartbeat daemon"
    exit 0
  fi
  # Write heartbeat
  date -u +%Y-%m-%dT%H:%M:%SZ > "$HB_FILE"
  sleep "$INTERVAL"
done
