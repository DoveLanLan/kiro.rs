---
name: team-stop
description: 优雅停止一个运行中的团队，支持 graceful shutdown。
---

# When to Use

When the user wants to stop a running team gracefully.

# Steps

1) List running teams:
   ```bash
   ./.osc/scripts/team.sh list
   ```

2) Confirm which team to stop (if only one, stop it directly).

3) Stop the team:
   ```bash
   ./.osc/scripts/team.sh stop <team-id>
   ```

4) Show the result.

# Shutdown Flow

The team uses graceful shutdown:
1. Write `.shutdown` signal file to notify agents to finish current work
2. Wait 30 seconds grace period
3. Send SIGTERM
4. Wait 10 more seconds
5. Final SIGKILL

# Notes

- After stopping, team status becomes `stopped`, agent worktrees are preserved
- To clean up worktrees: `./.osc/scripts/multi-agent/cleanup.sh <worktree-path>`
