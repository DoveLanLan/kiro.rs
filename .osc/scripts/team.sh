#!/usr/bin/env bash
set -euo pipefail

# Thin wrapper: delegates to team.js (Node.js implementation)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "$SCRIPT_DIR/team.cjs" "$@"
