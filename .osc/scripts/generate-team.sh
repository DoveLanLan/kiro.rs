#!/usr/bin/env bash
set -euo pipefail

# generate-team.sh: Analyze prd.md + project structure to auto-generate team config
#
# Usage: generate-team.sh <task-dir> [--output <path>]
# Output: YAML team config to stdout or file

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common/paths.sh"

usage() {
  echo "Usage: generate-team.sh <task-dir> [--output <path>]"
}

require_jq() {
  command -v jq >/dev/null 2>&1 || { echo "error: jq is required" >&2; exit 1; }
}

# Analyze prd.md for keywords to determine scope
analyze_prd() {
  local prd_file="$1"
  local prd_lower
  prd_lower="$(tr '[:upper:]' '[:lower:]' < "$prd_file")"

  # Detect characteristics
  local has_frontend=false has_backend=false has_api=false
  local has_bug=false has_refactor=false has_research=false
  local complexity="simple"  # simple | medium | complex

  # Frontend signals
  if echo "$prd_lower" | grep -qiE "frontend|前端|component|组件|页面|page|ui|ux|css|style|react|vue|angular|html|dom|browser|浏览器"; then
    has_frontend=true
  fi

  # Backend signals
  if echo "$prd_lower" | grep -qiE "backend|后端|api|接口|server|服务|database|数据库|db|sql|migration|endpoint|route|controller|service|middleware"; then
    has_backend=true
  fi

  # API signals (separate from backend for scope detection)
  if echo "$prd_lower" | grep -qiE "api|接口|endpoint|rest|graphql|grpc|websocket"; then
    has_api=true
  fi

  # Bug signals
  if echo "$prd_lower" | grep -qiE "bug|fix|修复|错误|error|crash|崩溃|问题|broken|报错|失败|regression"; then
    has_bug=true
  fi

  # Refactor signals
  if echo "$prd_lower" | grep -qiE "refactor|重构|优化|migrate|迁移|升级|upgrade|restructure|reorganize"; then
    has_refactor=true
  fi

  # Research signals
  if echo "$prd_lower" | grep -qiE "research|调研|investigate|探索|spike|prototype|原型|poc|proof.of.concept|evaluate|评估|compare|对比"; then
    has_research=true
  fi

  # Complexity estimation (by prd length and keyword density)
  local prd_lines
  prd_lines="$(wc -l < "$prd_file")"
  if [[ $prd_lines -gt 100 ]]; then
    complexity="complex"
  elif [[ $prd_lines -gt 30 ]]; then
    complexity="medium"
  fi

  # If both frontend and backend, bump complexity
  if $has_frontend && $has_backend; then
    if [[ "$complexity" == "simple" ]]; then
      complexity="medium"
    fi
  fi

  echo "$has_frontend $has_backend $has_api $has_bug $has_refactor $has_research $complexity"
}

# Scan project structure for additional signals
scan_project() {
  local root="$1"
  local has_src_frontend=false has_src_backend=false has_tests=false

  # Check common frontend directories
  for d in "src/components" "src/pages" "src/views" "app/components" "frontend" "client" "web"; do
    if [[ -d "$root/$d" ]]; then
      has_src_frontend=true
      break
    fi
  done

  # Check common backend directories
  for d in "src/api" "src/server" "src/services" "src/controllers" "src/routes" "backend" "server" "api"; do
    if [[ -d "$root/$d" ]]; then
      has_src_backend=true
      break
    fi
  done

  # Check for tests
  for d in "tests" "test" "__tests__" "spec" "src/__tests__" "src/test"; do
    if [[ -d "$root/$d" ]]; then
      has_tests=true
      break
    fi
  done

  echo "$has_src_frontend $has_src_backend $has_tests"
}

# Generate team YAML based on analysis
generate_yaml() {
  local has_frontend="$1" has_backend="$2" has_api="$3"
  local has_bug="$4" has_refactor="$5" has_research="$6"
  local complexity="$7"
  local proj_frontend="$8" proj_backend="$9" proj_tests="${10}"

  # Decide team pattern
  local team_name="auto-generated"
  local description=""
  local -a roles=()

  if [[ "$has_bug" == "true" ]]; then
    # Bug fix pattern
    team_name="auto-bugfix"
    description="Auto-generated bugfix team based on prd analysis"
    roles+=("debug:1:true:")
    roles+=("implement:2:true:debug")
    roles+=("check:3:true:implement")

  elif [[ "$has_research" == "true" ]]; then
    # Research/spike pattern
    team_name="auto-spike"
    description="Auto-generated spike/research team based on prd analysis"
    roles+=("research:1:true:")
    roles+=("plan:2:true:research")
    roles+=("implement:3:true:plan")
    roles+=("check:4:true:implement")

  elif [[ "$has_refactor" == "true" ]]; then
    # Refactor pattern
    team_name="auto-refactor"
    description="Auto-generated refactoring team based on prd analysis"
    roles+=("research:1:true:")
    roles+=("check:1:true:")
    roles+=("plan:2:true:research,check")
    roles+=("implement:3:true:plan")
    roles+=("debug:4:true:implement")

  elif [[ "$has_frontend" == "true" ]] && [[ "$has_backend" == "true" ]]; then
    # Full-stack pattern
    team_name="auto-fullstack"
    description="Auto-generated full-stack team (frontend + backend) based on prd analysis"
    roles+=("plan:1:true:")
    if [[ "$complexity" == "complex" ]]; then
      roles+=("research:1:false:")
    fi
    roles+=("implement:2:true:plan")
    roles+=("research:2:true:plan")
    roles+=("check:3:true:implement,research")

  else
    # Default feature pattern
    team_name="auto-feature"
    description="Auto-generated feature team based on prd analysis"
    roles+=("plan:1:true:")
    if [[ "$complexity" != "simple" ]]; then
      roles+=("research:1:false:")
    fi
    roles+=("implement:2:true:plan")
    roles+=("check:3:true:implement")
  fi

  # Output YAML
  echo "name: $team_name"
  echo "description: $description"
  echo "auto_generated: true"
  echo "roles:"

  for role_spec in "${roles[@]}"; do
    IFS=':' read -r agent phase auto_start deps <<< "$role_spec"
    echo "  - agent: $agent"
    echo "    phase: $phase"
    echo "    auto_start: $auto_start"
    if [[ -n "$deps" ]]; then
      echo "    depends_on:"
      IFS=',' read -ra dep_arr <<< "$deps"
      for dep in "${dep_arr[@]}"; do
        echo "      - $dep"
      done
    fi
  done
}

main() {
  local task_dir="" output_file=""

  local positional=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --output|-o) output_file="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) positional+=("$1"); shift ;;
    esac
  done
  task_dir="${positional[0]:-}"
  [[ -n "$task_dir" ]] || { echo "error: task-dir required" >&2; usage; exit 1; }

  local root
  root="$(osc_repo_root)"

  # Normalize
  if [[ "$task_dir" = /* ]]; then
    task_dir="${task_dir#$root/}"
  fi
  local abs_task="$root/$task_dir"
  [[ -d "$abs_task" ]] || { echo "error: task dir not found: $task_dir" >&2; exit 1; }

  # Read prd.md
  local prd_file="$abs_task/prd.md"
  if [[ ! -f "$prd_file" ]]; then
    # Try task.json description
    local task_json="$abs_task/task.json"
    if [[ -f "$task_json" ]]; then
      require_jq
      local desc
      desc="$(jq -r '.description // ""' "$task_json")"
      if [[ -n "$desc" ]]; then
        # Create temp file with description
        prd_file="$(mktemp)"
        echo "$desc" > "$prd_file"
        trap "rm -f '$prd_file'" EXIT
      else
        echo "error: no prd.md or task.json description found" >&2
        exit 1
      fi
    else
      echo "error: no prd.md found in $task_dir" >&2
      exit 1
    fi
  fi

  # Analyze
  local prd_result
  prd_result="$(analyze_prd "$prd_file")"
  read -r has_frontend has_backend has_api has_bug has_refactor has_research complexity <<< "$prd_result"

  local proj_result
  proj_result="$(scan_project "$root")"
  read -r proj_frontend proj_backend proj_tests <<< "$proj_result"

  # Log analysis
  echo "# Analysis results:" >&2
  echo "#   PRD: frontend=$has_frontend backend=$has_backend api=$has_api bug=$has_bug refactor=$has_refactor research=$has_research complexity=$complexity" >&2
  echo "#   Project: frontend=$proj_frontend backend=$proj_backend tests=$proj_tests" >&2

  # Generate
  local yaml_output
  yaml_output="$(generate_yaml "$has_frontend" "$has_backend" "$has_api" "$has_bug" "$has_refactor" "$has_research" "$complexity" "$proj_frontend" "$proj_backend" "$proj_tests")"

  if [[ -n "$output_file" ]]; then
    echo "$yaml_output" > "$output_file"
    echo "generated: $output_file" >&2
  else
    echo "$yaml_output"
  fi
}

main "$@"
