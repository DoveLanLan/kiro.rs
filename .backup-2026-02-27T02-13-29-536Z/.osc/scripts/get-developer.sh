#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"

name="$(osc_developer_name)"
if [[ -n "${name:-}" ]]; then
  echo "$name"
  exit 0
fi
exit 1

