#!/usr/bin/env bash
set -euo pipefail

# Minimal phase helpers (kept for compatibility with multi-agent scripts)

phase_label() {
  case "${1:-}" in
    0) echo "plan" ;;
    1) echo "implement" ;;
    2) echo "check" ;;
    *) echo "unknown" ;;
  esac
}

