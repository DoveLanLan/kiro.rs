---
name: team-start
description: 启动一个已创建的团队，在 git worktree 中启动各 agent 进程。
---

# When to Use

When the user wants to start a previously created team. The team must have been created via `team-create` first.

# Steps

1) List existing teams:
   ```bash
   ./.osc/scripts/team.sh list
   ```

2) If only one team exists, start it directly. If multiple, let the user choose.

3) Start the team:
   ```bash
   ./.osc/scripts/team.sh start <team-id>
   ```
   The runtime is auto-detected (claude for Claude Code, codex for Codex CLI).

4) Show the startup result (each agent's pid and worktree path).

5) Tell the user they can monitor progress with the `team-dashboard` skill.

# Notes

- Teams start agents in phase order (phase 1 first, later phases wait for dependencies)
- If no teams exist, guide the user to create one first with `team-create`
