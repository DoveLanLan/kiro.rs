# /osc:parallel

目标：在隔离的 git worktree 中并行推进任务（multi-agent pipeline）。

建议流程：

1) 创建任务：`./.osc/scripts/task.sh create "<title>"`
2) 启动 worktree：`./.osc/scripts/multi-agent/start.sh <task-dir>`
3) 查看状态：`./.osc/scripts/multi-agent/status.sh`
4) 需要清理：`./.osc/scripts/multi-agent/cleanup.sh <worktree-path>`

注意：这些脚本依赖 `git` 与 `jq`。

