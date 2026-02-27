#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"
source "$SCRIPT_DIR/common/runtime.sh"

usage() {
  cat <<'EOF'
Usage:
  ./.osc/scripts/agent.sh list [--json]
  ./.osc/scripts/agent.sh info <name>
  ./.osc/scripts/agent.sh match <capability>
  ./.osc/scripts/agent.sh match --task <task-dir>
EOF
}

# ---------------------------------------------------------------------------
# YAML helpers (simple grep/sed, no external parser)
# ---------------------------------------------------------------------------

agents_dir() {
  echo "$(osc_dir "$(osc_repo_root)")/agents"
}

# Read a scalar field from a YAML file: yaml_field <file> <key>
yaml_field() {
  local file="$1" key="$2"
  sed -n "s/^${key}: *//p" "$file" | head -n 1
}

# Read a list field from a YAML file: yaml_list <file> <key>
# Outputs one item per line (strips "  - " prefix).
yaml_list() {
  local file="$1" key="$2"
  local in_list=false
  while IFS= read -r line; do
    if [[ "$line" =~ ^${key}: ]]; then
      in_list=true
      continue
    fi
    if $in_list; then
      if [[ "$line" =~ ^[[:space:]]*-[[:space:]]+(.*) ]]; then
        echo "${BASH_REMATCH[1]}"
      else
        break
      fi
    fi
  done <"$file"
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_list() {
  local json=false
  if [[ "${1:-}" == "--json" ]]; then json=true; fi

  local dir
  dir="$(agents_dir)"
  [[ -d "$dir" ]] || { echo "error: agents dir not found: $dir" >&2; exit 1; }

  if $json; then
    local first=true
    echo "["
    for f in "$dir"/*.yaml; do
      [[ -f "$f" ]] || continue
      $first || echo ","
      first=false
      local name desc requires_task
      name="$(yaml_field "$f" name)"
      desc="$(yaml_field "$f" description)"
      requires_task="$(yaml_field "$f" requires_task)"

      local caps="" tools="" scopes=""
      while IFS= read -r c; do caps="${caps:+$caps, }\"$c\""; done < <(yaml_list "$f" capabilities)
      while IFS= read -r t; do tools="${tools:+$tools, }\"$t\""; done < <(yaml_list "$f" tools)
      while IFS= read -r s; do scopes="${scopes:+$scopes, }\"$s\""; done < <(yaml_list "$f" scope)

      printf '  {"name":"%s","description":"%s","capabilities":[%s],"scope":[%s],"tools":[%s],"requires_task":%s}' \
        "$name" "$desc" "$caps" "$scopes" "$tools" "${requires_task:-false}"
    done
    echo ""
    echo "]"
  else
    for f in "$dir"/*.yaml; do
      [[ -f "$f" ]] || continue
      local name desc
      name="$(yaml_field "$f" name)"
      desc="$(yaml_field "$f" description)"
      printf '%-12s %s\n' "$name" "$desc"
    done
  fi
}

cmd_info() {
  local name="${1:-}"
  [[ -n "$name" ]] || { echo "error: agent name required" >&2; usage; exit 1; }

  local file
  file="$(agents_dir)/${name}.yaml"
  [[ -f "$file" ]] || { echo "error: agent not found: $name" >&2; exit 1; }

  echo "Agent: $name"
  echo "---"
  echo "Description: $(yaml_field "$file" description)"
  echo "Requires task: $(yaml_field "$file" requires_task)"
  echo ""
  echo "Capabilities:"
  yaml_list "$file" capabilities | sed 's/^/  - /'
  echo ""
  echo "Scope:"
  yaml_list "$file" scope | sed 's/^/  - /'
  echo ""
  echo "Tools:"
  yaml_list "$file" tools | sed 's/^/  - /'
}

cmd_match() {
  # --task mode: map task type to capabilities, then match
  if [[ "${1:-}" == "--task" ]]; then
    local task_dir="${2:-}"
    [[ -n "$task_dir" ]] || { echo "error: task dir required" >&2; exit 1; }

    local root
    root="$(osc_repo_root)"
    local tj="$root/$task_dir/$FILE_TASK_JSON"
    [[ -f "$tj" ]] || { echo "error: task.json not found in $task_dir" >&2; exit 1; }

    command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }

    local task_type
    task_type="$(jq -r '.type // "feature"' "$tj" 2>/dev/null)"

    local -a caps
    case "$task_type" in
      feature)  caps=(code-edit doc-write task-create) ;;
      bugfix)   caps=(diagnostics code-edit) ;;
      hotfix)   caps=(diagnostics code-edit) ;;
      refactor) caps=(code-edit code-review) ;;
      docs)     caps=(doc-write doc-analysis) ;;
      *)        caps=(code-edit) ;;
    esac

    echo "Task type: $task_type"
    echo "Required capabilities: ${caps[*]}"
    echo "---"

    local dir
    dir="$(agents_dir)"
    for f in "$dir"/*.yaml; do
      [[ -f "$f" ]] || continue
      local agent_name
      agent_name="$(yaml_field "$f" name)"
      local agent_caps
      agent_caps="$(yaml_list "$f" capabilities)"
      for need in "${caps[@]}"; do
        if echo "$agent_caps" | grep -qx "$need"; then
          echo "$agent_name"
          break
        fi
      done
    done
    return 0
  fi

  # Simple capability match
  local capability="${1:-}"
  [[ -n "$capability" ]] || { echo "error: capability required" >&2; usage; exit 1; }

  local dir
  dir="$(agents_dir)"
  for f in "$dir"/*.yaml; do
    [[ -f "$f" ]] || continue
    if yaml_list "$f" capabilities | grep -qx "$capability"; then
      yaml_field "$f" name
    fi
  done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  local cmd="${1:-}"
  case "$cmd" in
    list)  shift; cmd_list "${1:-}" ;;
    info)  shift; cmd_info "${1:-}" ;;
    match) shift; cmd_match "$@" ;;
    ""|-h|--help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
