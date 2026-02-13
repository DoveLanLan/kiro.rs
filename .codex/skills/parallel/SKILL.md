---
name: parallel
description: 在隔离的 git worktree 中并行推进任务（multi-agent pipeline）。
---

# When to Use

When you want to run tasks in parallel using isolated git worktrees.

# Steps

1) Create a task:
   ```bash
   ./.osc/scripts/task.sh create "<title>"
   ```

2) Start worktree:
   ```bash
   ./.osc/scripts/multi-agent/start.sh <task-dir>
   ```

3) Check status:
   ```bash
   ./.osc/scripts/multi-agent/status.sh
   ```

4) Clean up when done:
   ```bash
   ./.osc/scripts/multi-agent/cleanup.sh <worktree-path>
   ```

# Notes

These scripts require `git` and `jq`.
