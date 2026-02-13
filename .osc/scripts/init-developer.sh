#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/developer.sh"

name="${1:-}"
if [[ -z "$name" ]]; then
  echo "Usage: $0 <your-name>" >&2
  exit 1
fi

osc_init_developer "$name"
echo "OK: developer initialized: $name"

