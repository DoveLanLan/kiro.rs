#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"
source "$SCRIPT_DIR/common/runtime.sh"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIR_TEAMS="teams"
DIR_TEAM_TEMPLATES="team-templates"

teams_dir() {
  echo "$(osc_dir "$(osc_repo_root)")/$DIR_TEAMS"
}

templates_dir() {
  echo "$(osc_dir "$(osc_repo_root)")/$DIR_TEAM_TEMPLATES"
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

usage() {
  cat <<'EOF'
Usage:
  ./.osc/scripts/team.sh create <task-dir> [--template feature-team]
  ./.osc/scripts/team.sh start <team-id> [--runtime claude|codex]
  ./.osc/scripts/team.sh status [<team-id>]
  ./.osc/scripts/team.sh stop <team-id>
  ./.osc/scripts/team.sh list
  ./.osc/scripts/team.sh send <team-id> --from <agent> --to <agent|*> --type <type> "<message>"
  ./.osc/scripts/team.sh inbox <team-id> --agent <agent> [--unread]
  ./.osc/scripts/team.sh dashboard <team-id>
  ./.osc/scripts/team.sh health <team-id>
  ./.osc/scripts/team.sh restart <team-id> <agent>
  ./.osc/scripts/team.sh watch <team-id> [--interval 30]
EOF
}

require_jq() {
  command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }
}

# ---------------------------------------------------------------------------
# YAML helpers (same approach as agent.sh)
# ---------------------------------------------------------------------------

yaml_field() {
  local file="$1" key="$2"
  sed -n "s/^${key}: *//p" "$file" | head -n 1
}

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
      elif [[ "$line" =~ ^[a-zA-Z_] ]]; then
        break
      fi
    fi
  done <"$file"
}

# Parse roles from template YAML. Each role is a block under "roles:" starting
# with "  - agent: <name>". Outputs one JSON object per role.
parse_template_roles() {
  local file="$1"
  require_jq

  local in_roles=false in_depends=false
  local agent="" phase="1" auto_start="true"
  local -a depends_on=()

  _flush_role() {
    if [[ -n "$agent" ]]; then
      local deps_json
      if [[ ${#depends_on[@]} -eq 0 ]]; then
        deps_json="[]"
      else
        deps_json="$(printf '%s\n' "${depends_on[@]}" | jq -R 'select(length>0)' | jq -sc '.')"
      fi
      jq -cn \
        --arg agent "$agent" \
        --argjson phase "$phase" \
        --argjson auto_start "$auto_start" \
        --argjson depends_on "$deps_json" \
        '{agent:$agent, phase:$phase, depends_on:$depends_on, auto_start:$auto_start, status:"pending"}'
    fi
    agent=""
    phase="1"
    auto_start="true"
    depends_on=()
  }

  while IFS= read -r line; do
    # Detect start of roles section
    if [[ "$line" =~ ^roles: ]]; then
      in_roles=true
      continue
    fi
    # End of roles section: non-indented, non-empty line
    if $in_roles && [[ "$line" =~ ^[a-zA-Z_] ]]; then
      break
    fi
    if ! $in_roles; then continue; fi

    # New role entry
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*agent:[[:space:]]*(.+) ]]; then
      _flush_role
      in_depends=false
      agent="${BASH_REMATCH[1]}"
      agent="${agent%%#*}"   # strip inline comments
      agent="${agent%% *}"   # strip trailing
      agent="$(echo "$agent" | tr -d '[:space:]')"
    elif [[ "$line" =~ ^[[:space:]]+phase:[[:space:]]*([0-9]+) ]]; then
      phase="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]+auto_start:[[:space:]]*(true|false) ]]; then
      auto_start="${BASH_REMATCH[1]}"
    elif [[ "$line" =~ ^[[:space:]]+depends_on:[[:space:]]*\[(.+)\] ]]; then
      # Inline format: depends_on: [plan, implement]
      local raw="${BASH_REMATCH[1]}"
      IFS=',' read -ra parts <<< "$raw"
      for p in "${parts[@]}"; do
        p="$(echo "$p" | tr -d '[:space:]')"
        [[ -n "$p" ]] && depends_on+=("$p")
      done
    elif [[ "$line" =~ ^[[:space:]]+depends_on:[[:space:]]*$ ]]; then
      # Multi-line format: depends_on:\n      - plan
      in_depends=true
    elif [[ "${in_depends:-false}" == "true" ]]; then
      if [[ "$line" =~ ^[[:space:]]+-[[:space:]]+(.+) ]]; then
        local dep="${BASH_REMATCH[1]}"
        dep="$(echo "$dep" | tr -d '[:space:]')"
        [[ -n "$dep" ]] && depends_on+=("$dep")
      else
        in_depends=false
      fi
    fi
  done <"$file"
  _flush_role
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_create() {
  require_jq
  local task_dir="" template="feature-team"

  # Parse args
  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --template|-t) template="$2"; shift 2 ;;
      *) positional+=("$1"); shift ;;
    esac
  done
  task_dir="${positional[0]:-}"
  [[ -n "$task_dir" ]] || { echo "error: task-dir required" >&2; usage; exit 1; }

  local root
  root="$(osc_repo_root)"

  # Normalize task_dir to relative
  if [[ "$task_dir" = /* ]]; then
    task_dir="${task_dir#$root/}"
  fi

  # Validate task dir exists
  [[ -d "$root/$task_dir" ]] || { echo "error: task dir not found: $task_dir" >&2; exit 1; }

  # Read template
  local tpl_file
  tpl_file="$(templates_dir)/${template}.yaml"
  [[ -f "$tpl_file" ]] || { echo "error: template not found: $tpl_file" >&2; exit 1; }

  # Parse roles
  local roles_json="[]"
  while IFS= read -r role_line; do
    [[ -n "$role_line" ]] || continue
    roles_json="$(echo "$roles_json" | jq --argjson r "$role_line" '. + [$r]')"
  done < <(parse_template_roles "$tpl_file")

  [[ "$(echo "$roles_json" | jq 'length')" -gt 0 ]] || { echo "error: no roles found in template" >&2; exit 1; }

  # Validate each agent exists
  local agent_script="$SCRIPT_DIR/agent.sh"
  if [[ -x "$agent_script" ]]; then
    for agent_name in $(echo "$roles_json" | jq -r '.[].agent'); do
      if ! "$agent_script" info "$agent_name" >/dev/null 2>&1; then
        echo "warn: agent '$agent_name' not found (skipping validation)" >&2
      fi
    done
  fi

  # Generate team-id
  local slug
  slug="$(basename "$task_dir" | sed -E 's/^[0-9]+-[0-9]+-//')"
  local team_id
  team_id="$(date +%Y%m%d)-${slug}"

  # Create team directory
  local team_dir
  team_dir="$(teams_dir)/$team_id"
  mkdir -p "$team_dir/agents"

  # Write team.json
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  jq -n \
    --arg id "$team_id" \
    --arg template "$template" \
    --arg task "$task_dir" \
    --arg created_at "$now" \
    --argjson roles "$roles_json" \
    '{id:$id, template:$template, task:$task, status:"created", created_at:$created_at, roles:$roles}' \
    >"$team_dir/team.json"

  echo "created team: $team_id"
  echo "  template: $template"
  echo "  task: $task_dir"
  echo "  roles: $(echo "$roles_json" | jq -r '[.[].agent] | join(", ")')"
}

cmd_start() {
  require_jq
  local team_id="" runtime=""

  # Parse args
  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --runtime|-r) runtime="$2"; shift 2 ;;
      *) positional+=("$1"); shift ;;
    esac
  done
  team_id="${positional[0]:-}"
  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }

  local root
  root="$(osc_repo_root)"
  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  # Detect runtime
  if [[ -z "$runtime" ]]; then
    runtime="$(detect_runtime)"
  fi
  case "$runtime" in
    claude|codex) ;;
    unknown) echo "error: cannot detect runtime (set OSC_RUNTIME or use --runtime)" >&2; exit 1 ;;
    *) echo "error: unsupported runtime: $runtime (use claude|codex)" >&2; exit 1 ;;
  esac
  echo "runtime: $runtime"

  local task_dir
  task_dir="$(jq -r '.task' "$team_json")"

  # Find the lowest phase with auto_start=true and no unmet dependencies
  local roles
  roles="$(jq -c '.roles[]' "$team_json")"
  local min_phase
  min_phase="$(jq -r '[.roles[] | select(.auto_start==true) | .phase] | min' "$team_json")"
  [[ "$min_phase" != "null" ]] || { echo "error: no auto_start roles found" >&2; exit 1; }

  echo "starting phase $min_phase agents..."

  local start_script="$SCRIPT_DIR/multi-agent/start.sh"
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  while IFS= read -r role; do
    local agent_name phase auto_start
    agent_name="$(echo "$role" | jq -r '.agent')"
    phase="$(echo "$role" | jq -r '.phase')"
    auto_start="$(echo "$role" | jq -r '.auto_start')"

    if [[ "$phase" -ne "$min_phase" ]]; then
      echo "  $agent_name [phase $phase] — deferred"
      continue
    fi
    if [[ "$auto_start" != "true" ]]; then
      echo "  $agent_name [phase $phase] — auto_start=false, skipped"
      continue
    fi

    # Create agent state file
    local agent_json="$team_dir/agents/${agent_name}.json"
    jq -n \
      --arg agent "$agent_name" \
      --arg runtime "$runtime" \
      --arg started_at "$now" \
      '{agent:$agent, status:"running", pid:null, worktree:null, started_at:$started_at, runtime:$runtime}' \
      >"$agent_json"

    # Start the agent via multi-agent/start.sh or runtime binary
    local pid="" worktree=""
    if [[ -x "$start_script" ]]; then
      # start.sh creates worktree and optionally starts claude
      local start_output
      start_output="$("$start_script" "$task_dir" 2>&1)" || {
        echo "  $agent_name [error] — start.sh failed"
        jq --arg s "error" '.status=$s' "$agent_json" > "${agent_json}.tmp" && mv "${agent_json}.tmp" "$agent_json"
        continue
      }
      # Extract worktree and pid from output
      worktree="$(echo "$start_output" | grep -oP '(?<=worktree: ).+' || true)"
      pid="$(echo "$start_output" | grep -oP '(?<=pid: )\d+' || true)"
    else
      echo "  warn: multi-agent/start.sh not found; creating state only" >&2
    fi

    # Update agent state with pid/worktree
    local tmp="${agent_json}.tmp"
    jq \
      --arg pid "${pid:-}" \
      --arg wt "${worktree:-}" \
      '.pid=(if $pid == "" then null else ($pid|tonumber) end) | .worktree=(if $wt == "" then null else $wt end)' \
      "$agent_json" >"$tmp" && mv "$tmp" "$agent_json"

    echo "  $agent_name [started] pid=${pid:-n/a} worktree=${worktree:-n/a}"
  done <<< "$roles"

  # Update team status
  local tmp="${team_json}.tmp"
  jq --arg s "running" --arg rt "$runtime" '.status=$s | .runtime=$rt' "$team_json" >"$tmp" && mv "$tmp" "$team_json"
  echo "team $team_id is running"
}

cmd_status() {
  require_jq
  local team_id="${1:-}"
  local root
  root="$(osc_repo_root)"
  local base
  base="$(teams_dir)"

  if [[ -n "$team_id" ]]; then
    _show_team_status "$base/$team_id"
  else
    # Show all teams
    if [[ ! -d "$base" ]]; then
      echo "no teams found"
      return 0
    fi
    local found=false
    for d in "$base"/*/; do
      [[ -f "$d/team.json" ]] || continue
      found=true
      _show_team_status "$d"
      echo ""
    done
    if ! $found; then
      echo "no teams found"
    fi
  fi
}

_show_team_status() {
  local team_dir="${1%/}"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team.json not found in $team_dir" >&2; return 1; }

  local id template task status
  id="$(jq -r '.id' "$team_json")"
  template="$(jq -r '.template' "$team_json")"
  task="$(jq -r '.task' "$team_json")"
  status="$(jq -r '.status' "$team_json")"

  echo "Team: $id [$status]"
  echo "Template: $template | Task: $task"
  echo "---"

  # Show each role
  while IFS= read -r role; do
    local agent_name role_status depends_on
    agent_name="$(echo "$role" | jq -r '.agent')"
    role_status="$(echo "$role" | jq -r '.status')"
    depends_on="$(echo "$role" | jq -r '.depends_on | if length > 0 then join(", ") else "" end')"

    local agent_json="$team_dir/agents/${agent_name}.json"
    if [[ -f "$agent_json" ]]; then
      local pid wt agent_status
      pid="$(jq -r '.pid // empty' "$agent_json")"
      wt="$(jq -r '.worktree // empty' "$agent_json")"
      agent_status="$(jq -r '.status' "$agent_json")"

      # Check if PID is still alive
      if [[ -n "$pid" && "$agent_status" == "running" ]]; then
        if ! kill -0 "$pid" 2>/dev/null; then
          agent_status="exited"
          # Update the file
          local tmp="${agent_json}.tmp"
          jq '.status="exited"' "$agent_json" >"$tmp" && mv "$tmp" "$agent_json"
        fi
      fi

      printf '  %-14s [%-8s]  pid=%-8s worktree=%s\n' \
        "$agent_name" "$agent_status" "${pid:-n/a}" "${wt:-n/a}"
    else
      if [[ -n "$depends_on" ]]; then
        printf '  %-14s [%-8s]  (waiting for: %s)\n' "$agent_name" "$role_status" "$depends_on"
      else
        printf '  %-14s [%-8s]\n' "$agent_name" "$role_status"
      fi
    fi
  done < <(jq -c '.roles[]' "$team_json")
}

cmd_stop() {
  require_jq
  local team_id="${1:-}"
  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  echo "stopping team $team_id..."

  # Stop each running agent
  for agent_json in "$team_dir"/agents/*.json; do
    [[ -f "$agent_json" ]] || continue
    local agent_name pid agent_status
    agent_name="$(jq -r '.agent' "$agent_json")"
    pid="$(jq -r '.pid // empty' "$agent_json")"
    agent_status="$(jq -r '.status' "$agent_json")"

    if [[ "$agent_status" != "running" ]]; then
      echo "  $agent_name [$agent_status] — skip"
      continue
    fi

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      # Write shutdown signal file for graceful shutdown
      touch "$team_dir/agents/${agent_name}.shutdown"

      # Wait up to 30s for agent to notice signal file and exit
      local waited=0
      while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 30 ]]; do
        sleep 1
        waited=$((waited + 1))
      done

      if kill -0 "$pid" 2>/dev/null; then
        # SIGTERM
        kill "$pid" 2>/dev/null || true
        # Wait up to 10s after SIGTERM
        waited=0
        while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 10 ]]; do
          sleep 1
          waited=$((waited + 1))
        done
        # SIGKILL if still alive
        if kill -0 "$pid" 2>/dev/null; then
          kill -9 "$pid" 2>/dev/null || true
          echo "  $agent_name — killed (SIGKILL)"
        else
          echo "  $agent_name — stopped (SIGTERM)"
        fi
      else
        echo "  $agent_name — stopped (graceful)"
      fi

      # Clean up signal and heartbeat files
      rm -f "$team_dir/agents/${agent_name}.shutdown" "$team_dir/agents/${agent_name}.heartbeat"
    else
      echo "  $agent_name — not running (pid=${pid:-n/a})"
    fi

    # Update agent state
    local tmp="${agent_json}.tmp"
    jq '.status="stopped"' "$agent_json" >"$tmp" && mv "$tmp" "$agent_json"
  done

  # Update team status
  local tmp="${team_json}.tmp"
  jq '.status="stopped"' "$team_json" >"$tmp" && mv "$tmp" "$team_json"
  echo "team $team_id stopped"
}

cmd_list() {
  require_jq
  local base
  base="$(teams_dir)"

  if [[ ! -d "$base" ]]; then
    echo "no teams found"
    return 0
  fi

  local found=false
  printf '%-28s %-16s %-40s %-10s %s\n' "TEAM" "TEMPLATE" "TASK" "STATUS" "AGENTS"
  printf '%-28s %-16s %-40s %-10s %s\n' "----" "--------" "----" "------" "------"

  for d in "$base"/*/; do
    local tj="$d/team.json"
    [[ -f "$tj" ]] || continue
    found=true

    local id template task status agent_count
    id="$(jq -r '.id' "$tj")"
    template="$(jq -r '.template' "$tj")"
    task="$(jq -r '.task' "$tj")"
    status="$(jq -r '.status' "$tj")"
    agent_count="$(jq '.roles | length' "$tj")"

    printf '%-28s %-16s %-40s %-10s %s\n' "$id" "$template" "$task" "$status" "$agent_count"
  done

  if ! $found; then
    echo "no teams found"
  fi
}

# ---------------------------------------------------------------------------
# Scope conflict detection
# ---------------------------------------------------------------------------

_check_scope_conflicts() {
  local team_dir="${1%/}"
  local agents_dir="$team_dir/agents"
  [[ -d "$agents_dir" ]] || return 0

  local -a names=()
  local -a scopes=()
  local -a locked=()

  for agent_json in "$agents_dir"/*.json; do
    [[ -f "$agent_json" ]] || continue
    local name
    name="$(jq -r '.agent' "$agent_json")"
    local scope_list
    scope_list="$(jq -r '.scope // [] | .[]' "$agent_json" 2>/dev/null)"
    local locked_list
    locked_list="$(jq -r '.locked_files // [] | .[]' "$agent_json" 2>/dev/null)"
    names+=("$name")
    scopes+=("$scope_list")
    locked+=("$locked_list")
  done

  local conflicts=0
  local count=${#names[@]}
  for ((i=0; i<count; i++)); do
    for ((j=i+1; j<count; j++)); do
      # Check scope overlaps (exact string match)
      while IFS= read -r s; do
        [[ -n "$s" ]] || continue
        if echo "${scopes[$j]}" | grep -qxF "$s"; then
          echo "warning: scope conflict — ${names[$i]} and ${names[$j]} both claim: $s" >&2
          conflicts=$((conflicts + 1))
        fi
      done <<< "${scopes[$i]}"
      # Check locked_files overlaps
      while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        if echo "${locked[$j]}" | grep -qxF "$f"; then
          echo "warning: locked file conflict — ${names[$i]} and ${names[$j]} both lock: $f" >&2
          conflicts=$((conflicts + 1))
        fi
      done <<< "${locked[$i]}"
    done
  done

  return $conflicts
}

# ---------------------------------------------------------------------------
# Communication subcommands
# ---------------------------------------------------------------------------

cmd_send() {
  require_jq
  local team_id="" from="" to="" msg_type="" message=""

  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --from)  from="$2"; shift 2 ;;
      --to)    to="$2"; shift 2 ;;
      --type)  msg_type="$2"; shift 2 ;;
      *)       positional+=("$1"); shift ;;
    esac
  done
  team_id="${positional[0]:-}"
  message="${positional[1]:-}"

  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }
  [[ -n "$from" ]]    || { echo "error: --from required" >&2; exit 1; }
  [[ -n "$to" ]]      || { echo "error: --to required" >&2; exit 1; }
  [[ -n "$msg_type" ]] || { echo "error: --type required" >&2; exit 1; }
  [[ -n "$message" ]]  || { echo "error: message required" >&2; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  [[ -f "$team_dir/team.json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  mkdir -p "$team_dir/messages"

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local filename
  filename="$(date +%Y%m%dT%H%M%S)-${from}.json"

  jq -n \
    --arg from "$from" \
    --arg to "$to" \
    --arg type "$msg_type" \
    --arg content "$message" \
    --arg timestamp "$ts" \
    '{from:$from, to:$to, type:$type, content:$content, timestamp:$timestamp}' \
    >"$team_dir/messages/$filename"

  echo "sent message from=$from to=$to type=$msg_type"
}

cmd_inbox() {
  require_jq
  local team_id="" agent="" unread=false

  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --agent)  agent="$2"; shift 2 ;;
      --unread) unread=true; shift ;;
      *)        positional+=("$1"); shift ;;
    esac
  done
  team_id="${positional[0]:-}"

  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }
  [[ -n "$agent" ]]   || { echo "error: --agent required" >&2; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  [[ -f "$team_dir/team.json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  local msg_dir="$team_dir/messages"
  if [[ ! -d "$msg_dir" ]] || [ -z "$(ls -A "$msg_dir" 2>/dev/null)" ]; then
    echo "0 message(s)"
    return 0
  fi

  local last_read=""
  local last_read_file="$team_dir/agents/${agent}.last-read"
  if $unread && [[ -f "$last_read_file" ]]; then
    last_read="$(cat "$last_read_file")"
  fi

  local count=0
  for msg_file in "$msg_dir"/*.json; do
    [[ -f "$msg_file" ]] || continue

    local msg_to
    msg_to="$(jq -r '.to' "$msg_file")"
    # Filter: must be addressed to this agent or broadcast
    if [[ "$msg_to" != "$agent" && "$msg_to" != "*" ]]; then
      continue
    fi

    # Filter by unread if requested
    if $unread && [[ -n "$last_read" ]]; then
      local msg_ts
      msg_ts="$(jq -r '.timestamp' "$msg_file")"
      if [[ "$msg_ts" < "$last_read" || "$msg_ts" == "$last_read" ]]; then
        continue
      fi
    fi

    local msg_from msg_type msg_ts msg_content
    msg_from="$(jq -r '.from' "$msg_file")"
    msg_type="$(jq -r '.type' "$msg_file")"
    msg_ts="$(jq -r '.timestamp' "$msg_file")"
    msg_content="$(jq -r '.content' "$msg_file")"

    echo "[from: $msg_from | type: $msg_type | $msg_ts]"
    echo "$msg_content"
    echo ""
    count=$((count + 1))
  done

  # Update last-read timestamp
  mkdir -p "$(dirname "$last_read_file")"
  date -u +%Y-%m-%dT%H:%M:%SZ >"$last_read_file"

  echo "$count message(s)"
}

cmd_dashboard() {
  require_jq
  local team_id="${1:-}"
  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  # --- Section 1: Team overview ---
  local id template task status created_at
  id="$(jq -r '.id' "$team_json")"
  template="$(jq -r '.template' "$team_json")"
  task="$(jq -r '.task' "$team_json")"
  status="$(jq -r '.status' "$team_json")"
  created_at="$(jq -r '.created_at' "$team_json")"

  echo "=== Team Dashboard: $id ==="
  echo "Template: $template | Task: $task"
  echo "Status: $status | Created: $created_at"
  echo ""

  # --- Section 2: Agent details ---
  echo "--- Agents ---"
  local root
  root="$(osc_repo_root)"

  while IFS= read -r role; do
    local agent_name
    agent_name="$(echo "$role" | jq -r '.agent')"
    local agent_json="$team_dir/agents/${agent_name}.json"

    if [[ -f "$agent_json" ]]; then
      local agent_status pid wt
      agent_status="$(jq -r '.status' "$agent_json")"
      pid="$(jq -r '.pid // empty' "$agent_json")"
      wt="$(jq -r '.worktree // empty' "$agent_json")"

      # Check if PID is still alive
      if [[ -n "$pid" && "$agent_status" == "running" ]]; then
        if ! kill -0 "$pid" 2>/dev/null; then
          agent_status="exited"
        fi
      fi

      printf '  %-14s [%-8s]  pid=%-8s\n' "$agent_name" "$agent_status" "${pid:-n/a}"

      # Last progress line from worktree
      if [[ -n "$wt" && -f "$root/$wt/progress.log" ]]; then
        local last_line
        last_line="$(tail -n 1 "$root/$wt/progress.log" 2>/dev/null || true)"
        if [[ -n "$last_line" ]]; then
          echo "    last: $last_line"
        fi
      fi
    else
      local depends_on
      depends_on="$(echo "$role" | jq -r '.depends_on | if length > 0 then join(", ") else "" end')"
      if [[ -n "$depends_on" ]]; then
        printf '  %-14s [pending ]  (waiting for: %s)\n' "$agent_name" "$depends_on"
      else
        printf '  %-14s [pending ]\n' "$agent_name"
      fi
    fi
  done < <(jq -c '.roles[]' "$team_json")
  echo ""

  # --- Section 3: Unread message counts ---
  echo "--- Messages ---"
  local msg_dir="$team_dir/messages"
  if [[ -d "$msg_dir" ]] && [ -n "$(ls -A "$msg_dir" 2>/dev/null)" ]; then
    while IFS= read -r role; do
      local agent_name
      agent_name="$(echo "$role" | jq -r '.agent')"
      local last_read_file="$team_dir/agents/${agent_name}.last-read"
      local last_read=""
      if [[ -f "$last_read_file" ]]; then
        last_read="$(cat "$last_read_file")"
      fi

      local unread_count=0
      for msg_file in "$msg_dir"/*.json; do
        [[ -f "$msg_file" ]] || continue
        local msg_to
        msg_to="$(jq -r '.to' "$msg_file")"
        if [[ "$msg_to" != "$agent_name" && "$msg_to" != "*" ]]; then
          continue
        fi
        if [[ -n "$last_read" ]]; then
          local msg_ts
          msg_ts="$(jq -r '.timestamp' "$msg_file")"
          if [[ "$msg_ts" < "$last_read" || "$msg_ts" == "$last_read" ]]; then
            continue
          fi
        fi
        unread_count=$((unread_count + 1))
      done

      if [[ $unread_count -gt 0 ]]; then
        echo "  $agent_name: $unread_count unread"
      else
        echo "  $agent_name: 0 unread"
      fi
    done < <(jq -c '.roles[]' "$team_json")
  else
    echo "  (no messages)"
  fi
  echo ""

  # --- Section 4: Scope conflicts ---
  echo "--- Scope Conflicts ---"
  if ! _check_scope_conflicts "$team_dir" 2>&1; then
    : # warnings already printed
  else
    echo "  (none)"
  fi
}

# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

_read_lifecycle_config() {
  local agent_name="$1"
  local root
  root="$(osc_repo_root)"
  local agent_yaml="$(osc_dir "$root")/agents/${agent_name}.yaml"

  local restart="never" max_restarts="3" timeout_minutes="60" hb_interval="30"
  if [[ -f "$agent_yaml" ]]; then
    local v
    v="$(sed -n 's/^  restart: *//p' "$agent_yaml" | head -n1)"
    [[ -n "$v" ]] && restart="$v"
    v="$(sed -n 's/^  max_restarts: *//p' "$agent_yaml" | head -n1)"
    [[ -n "$v" ]] && max_restarts="$v"
    v="$(sed -n 's/^  timeout_minutes: *//p' "$agent_yaml" | head -n1)"
    [[ -n "$v" ]] && timeout_minutes="$v"
    v="$(sed -n 's/^  heartbeat_interval: *//p' "$agent_yaml" | head -n1)"
    [[ -n "$v" ]] && hb_interval="$v"
  fi

  echo "$restart $max_restarts $timeout_minutes $hb_interval"
}

_format_uptime() {
  local seconds="$1"
  if [[ $seconds -ge 3600 ]]; then
    printf '%dh %dm' $((seconds / 3600)) $(( (seconds % 3600) / 60 ))
  else
    printf '%dm' $((seconds / 60))
  fi
}

cmd_health() {
  require_jq
  local team_id="${1:-}"
  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  local now_epoch
  now_epoch="$(date +%s)"

  echo "Health: $team_id"
  echo "---"

  while IFS= read -r role; do
    local agent_name
    agent_name="$(echo "$role" | jq -r '.agent')"
    local agent_json="$team_dir/agents/${agent_name}.json"

    if [[ ! -f "$agent_json" ]]; then
      printf '  %-14s [%-10s]\n' "$agent_name" "pending"
      continue
    fi

    local pid agent_status started_at
    pid="$(jq -r '.pid // empty' "$agent_json")"
    agent_status="$(jq -r '.status' "$agent_json")"
    started_at="$(jq -r '.started_at // empty' "$agent_json")"

    # Calculate uptime
    local uptime_str="n/a"
    if [[ -n "$started_at" ]]; then
      local start_epoch
      start_epoch="$(date -d "$started_at" +%s 2>/dev/null || echo 0)"
      if [[ $start_epoch -gt 0 ]]; then
        local uptime_secs=$(( now_epoch - start_epoch ))
        uptime_str="$(_format_uptime $uptime_secs)"
      fi
    fi

    # Check heartbeat
    local hb_file="$team_dir/agents/${agent_name}.heartbeat"
    local hb_str="no-hb"
    local hb_age=-1
    if [[ -f "$hb_file" ]]; then
      local hb_ts
      hb_ts="$(cat "$hb_file")"
      local hb_epoch
      hb_epoch="$(date -d "$hb_ts" +%s 2>/dev/null || echo 0)"
      if [[ $hb_epoch -gt 0 ]]; then
        hb_age=$(( now_epoch - hb_epoch ))
        hb_str="${hb_age}s ago"
      fi
    fi

    # Check PID alive
    local pid_alive=false
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      pid_alive=true
    fi

    # Read lifecycle config for timeout
    local lc
    lc="$(_read_lifecycle_config "$agent_name")"
    local timeout_minutes
    timeout_minutes="$(echo "$lc" | awk '{print $3}')"

    # Determine health status
    local health="dead"
    if [[ "$agent_status" != "running" && "$agent_status" != "error" ]]; then
      health="$agent_status"
    elif $pid_alive; then
      # Check timeout first
      if [[ -n "$started_at" ]]; then
        local start_epoch
        start_epoch="$(date -d "$started_at" +%s 2>/dev/null || echo 0)"
        if [[ $start_epoch -gt 0 ]]; then
          local uptime_secs=$(( now_epoch - start_epoch ))
          local timeout_secs=$(( timeout_minutes * 60 ))
          if [[ $uptime_secs -gt $timeout_secs ]]; then
            health="timed-out"
          elif [[ $hb_age -ge 0 && $hb_age -lt 120 ]]; then
            health="healthy"
          elif [[ $hb_age -ge 120 && $hb_age -le 300 ]]; then
            health="stale"
          elif [[ $hb_age -lt 0 ]]; then
            # No heartbeat file but PID alive
            health="stale"
          else
            # heartbeat > 300s
            health="dead"
          fi
        fi
      else
        if [[ $hb_age -ge 0 && $hb_age -lt 120 ]]; then
          health="healthy"
        else
          health="stale"
        fi
      fi
    fi

    printf '  %-14s [%-10s]  heartbeat=%-10s uptime=%s\n' \
      "$agent_name" "$health" "$hb_str" "$uptime_str"
  done < <(jq -c '.roles[]' "$team_json")
}

cmd_restart() {
  require_jq
  local team_id="${1:-}" agent_name="${2:-}"
  [[ -n "$team_id" ]]    || { echo "error: team-id required" >&2; usage; exit 1; }
  [[ -n "$agent_name" ]] || { echo "error: agent name required" >&2; usage; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  local agent_json="$team_dir/agents/${agent_name}.json"
  [[ -f "$agent_json" ]] || { echo "error: agent not found: $agent_name" >&2; exit 1; }

  local pid
  pid="$(jq -r '.pid // empty' "$agent_json")"

  # Stop the agent if running
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "stopping $agent_name (pid=$pid)..."
    kill "$pid" 2>/dev/null || true
    local waited=0
    while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 5 ]]; do
      sleep 1
      waited=$((waited + 1))
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi

  # Clean up signal/heartbeat files
  rm -f "$team_dir/agents/${agent_name}.shutdown" "$team_dir/agents/${agent_name}.heartbeat"

  # Read and increment restart count
  local restart_count
  restart_count="$(jq -r '.restart_count // 0' "$agent_json")"
  restart_count=$((restart_count + 1))

  local task_dir
  task_dir="$(jq -r '.task' "$team_json")"

  # Re-launch via multi-agent/start.sh
  local start_script="$SCRIPT_DIR/multi-agent/start.sh"
  local new_pid="" new_worktree=""
  if [[ -x "$start_script" ]]; then
    local start_output
    start_output="$("$start_script" "$task_dir" 2>&1)" || {
      echo "error: start.sh failed for $agent_name" >&2
      jq --arg s "error" --argjson rc "$restart_count" \
        '.status=$s | .restart_count=$rc' "$agent_json" > "${agent_json}.tmp" && mv "${agent_json}.tmp" "$agent_json"
      return 1
    }
    new_worktree="$(echo "$start_output" | grep -oP '(?<=worktree: ).+' || true)"
    new_pid="$(echo "$start_output" | grep -oP '(?<=pid: )\d+' || true)"
  else
    echo "warn: multi-agent/start.sh not found; updating state only" >&2
  fi

  # Update agent JSON
  local now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local tmp="${agent_json}.tmp"
  jq \
    --arg pid "${new_pid:-}" \
    --arg wt "${new_worktree:-}" \
    --arg started_at "$now" \
    --argjson rc "$restart_count" \
    '.status="running" | .started_at=$started_at | .restart_count=$rc |
     .pid=(if $pid == "" then null else ($pid|tonumber) end) |
     .worktree=(if $wt == "" then null else $wt end)' \
    "$agent_json" >"$tmp" && mv "$tmp" "$agent_json"

  echo "$agent_name restarted (restart_count=$restart_count) pid=${new_pid:-n/a}"
}

cmd_watch() {
  require_jq
  local team_id="" interval=30

  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      *) positional+=("$1"); shift ;;
    esac
  done
  team_id="${positional[0]:-}"
  [[ -n "$team_id" ]] || { echo "error: team-id required" >&2; usage; exit 1; }

  local team_dir
  team_dir="$(teams_dir)/$team_id"
  local team_json="$team_dir/team.json"
  [[ -f "$team_json" ]] || { echo "error: team not found: $team_id" >&2; exit 1; }

  trap 'echo "watch stopped"; exit 0' INT TERM

  echo "watching team $team_id (interval=${interval}s) — Ctrl+C to stop"

  while true; do
    local now_epoch
    now_epoch="$(date +%s)"
    echo ""
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

    while IFS= read -r role; do
      local agent_name
      agent_name="$(echo "$role" | jq -r '.agent')"
      local agent_json="$team_dir/agents/${agent_name}.json"

      if [[ ! -f "$agent_json" ]]; then
        printf '  %-14s [%-10s]\n' "$agent_name" "pending"
        continue
      fi

      local pid agent_status started_at
      pid="$(jq -r '.pid // empty' "$agent_json")"
      agent_status="$(jq -r '.status' "$agent_json")"
      started_at="$(jq -r '.started_at // empty' "$agent_json")"

      # Uptime
      local uptime_str="n/a"
      if [[ -n "$started_at" ]]; then
        local start_epoch
        start_epoch="$(date -d "$started_at" +%s 2>/dev/null || echo 0)"
        if [[ $start_epoch -gt 0 ]]; then
          uptime_str="$(_format_uptime $(( now_epoch - start_epoch )))"
        fi
      fi

      # Heartbeat
      local hb_file="$team_dir/agents/${agent_name}.heartbeat"
      local hb_str="no-hb" hb_age=-1
      if [[ -f "$hb_file" ]]; then
        local hb_epoch
        hb_epoch="$(date -d "$(cat "$hb_file")" +%s 2>/dev/null || echo 0)"
        if [[ $hb_epoch -gt 0 ]]; then
          hb_age=$(( now_epoch - hb_epoch ))
          hb_str="${hb_age}s ago"
        fi
      fi

      # PID check
      local pid_alive=false
      if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        pid_alive=true
      fi

      # Lifecycle config
      local lc
      lc="$(_read_lifecycle_config "$agent_name")"
      local lc_restart lc_max_restarts lc_timeout
      lc_restart="$(echo "$lc" | awk '{print $1}')"
      lc_max_restarts="$(echo "$lc" | awk '{print $2}')"
      lc_timeout="$(echo "$lc" | awk '{print $3}')"

      # Determine health
      local health="dead"
      if [[ "$agent_status" != "running" && "$agent_status" != "error" ]]; then
        health="$agent_status"
      elif $pid_alive; then
        if [[ -n "$started_at" ]]; then
          local start_epoch
          start_epoch="$(date -d "$started_at" +%s 2>/dev/null || echo 0)"
          if [[ $start_epoch -gt 0 ]]; then
            local uptime_secs=$(( now_epoch - start_epoch ))
            local timeout_secs=$(( lc_timeout * 60 ))
            if [[ $uptime_secs -gt $timeout_secs ]]; then
              health="timed-out"
            elif [[ $hb_age -ge 0 && $hb_age -lt 120 ]]; then
              health="healthy"
            elif [[ $hb_age -ge 120 && $hb_age -le 300 ]]; then
              health="stale"
            elif [[ $hb_age -lt 0 ]]; then
              health="stale"
            else
              health="dead"
            fi
          fi
        else
          if [[ $hb_age -ge 0 && $hb_age -lt 120 ]]; then
            health="healthy"
          else
            health="stale"
          fi
        fi
      fi

      printf '  %-14s [%-10s]  heartbeat=%-10s uptime=%s\n' \
        "$agent_name" "$health" "$hb_str" "$uptime_str"

      # Auto-restart dead or timed-out agents
      if [[ "$health" == "dead" || "$health" == "timed-out" ]]; then
        local restart_count
        restart_count="$(jq -r '.restart_count // 0' "$agent_json")"

        if [[ "$lc_restart" == "never" ]]; then
          echo "    → not restarting (policy=never)"
        elif [[ $restart_count -ge $lc_max_restarts ]]; then
          echo "    → max restarts exceeded ($restart_count/$lc_max_restarts)"
        elif [[ "$lc_restart" == "always" || "$lc_restart" == "on-failure" ]]; then
          echo "    → auto-restarting ($lc_restart, count=$restart_count)..."
          cmd_restart "$team_id" "$agent_name"
        fi
      fi
    done < <(jq -c '.roles[]' "$team_json")

    sleep "$interval"
  done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  local cmd="${1:-}"
  case "$cmd" in
    create)    shift; cmd_create "$@" ;;
    start)     shift; cmd_start "$@" ;;
    status)    shift; cmd_status "${1:-}" ;;
    stop)      shift; cmd_stop "${1:-}" ;;
    list)      shift; cmd_list ;;
    send)      shift; cmd_send "$@" ;;
    inbox)     shift; cmd_inbox "$@" ;;
    dashboard) shift; cmd_dashboard "${1:-}" ;;
    health)    shift; cmd_health "${1:-}" ;;
    restart)   shift; cmd_restart "$@" ;;
    watch)     shift; cmd_watch "$@" ;;
    ""|-h|--help) usage ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"
