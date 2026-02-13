#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"
source "$SCRIPT_DIR/common/task-utils.sh"

usage() {
  cat <<'EOF'
Usage:
  ./.osc/scripts/add-session.sh --title "..." [--commit <sha>] [--notes "<text>"]
EOF
}

title="" commit="" notes=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) title="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --notes) notes="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "error: unknown arg: $1" >&2; exit 1 ;;
  esac
done

root="$(osc_repo_root)"
dev="$(osc_developer_name "$root")"
if [[ -z "${dev:-}" ]]; then
  echo "error: developer not set. Run ./.osc/scripts/init-developer.sh <name> (or open-spec-code init -u <name>)" >&2
  exit 1
fi

ws="$(osc_workspace_dir "$root")"
mkdir -p "$ws"

n="$(osc_next_journal_number "$root")"
j="$ws/${FILE_JOURNAL_PREFIX}${n}.md"

cat >"$j" <<EOF
# ${dev} journal ${n}

- Date: $(date -u +%Y-%m-%d)
- Title: ${title:-Session}
- Commit: ${commit:-}

## Summary
${notes:-}
EOF

# Update per-dev index
idx="$ws/index.md"
if [[ ! -f "$idx" ]]; then
  echo "# ${dev} workspace" >"$idx"
  echo "" >>"$idx"
  echo "## Journals" >>"$idx"
  echo "" >>"$idx"
fi
echo "- ${FILE_JOURNAL_PREFIX}${n}.md — ${title:-Session}" >>"$idx"

echo "write: ${j#$root/}"
echo "update: ${idx#$root/}"

