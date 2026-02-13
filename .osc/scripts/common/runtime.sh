#!/usr/bin/env bash
set -euo pipefail

# runtime.sh — detect which AI CLI runtime is active (claude / codex)

_RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect runtime: OSC_RUNTIME env > binary probe > unknown
detect_runtime() {
  if [[ -n "${OSC_RUNTIME:-}" ]]; then
    echo "$OSC_RUNTIME"
    return 0
  fi
  if command -v claude >/dev/null 2>&1; then
    echo "claude"
    return 0
  fi
  if command -v codex >/dev/null 2>&1; then
    echo "codex"
    return 0
  fi
  echo "unknown"
  return 0
}

# Ensure runtime is known; exit 1 if unknown
ensure_runtime() {
  local rt
  rt="$(detect_runtime)"
  if [[ "$rt" == "unknown" ]]; then
    echo "error: cannot detect runtime (set OSC_RUNTIME=claude|codex or ensure binary is in PATH)" >&2
    return 1
  fi
  echo "$rt"
}
