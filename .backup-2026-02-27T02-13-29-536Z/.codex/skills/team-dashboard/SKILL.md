---
name: team-dashboard
description: 查看团队的综合状态面板，包括 agent 健康状态和建议操作。
---

# When to Use

When the user wants to check the status of a running team, see agent health, or get recommendations for next actions.

# Steps

1) List teams:
   ```bash
   ./.osc/scripts/team.sh list
   ```

2) Show dashboard:
   ```bash
   ./.osc/scripts/team.sh dashboard <team-id>
   ```

3) Show health status:
   ```bash
   ./.osc/scripts/team.sh health <team-id>
   ```

4) Give recommendations based on status:
   - Dead agent → suggest `./.osc/scripts/team.sh restart <team-id> <agent>`
   - Stale agent → suggest checking or waiting
   - Scope conflict → remind user about merge conflicts
   - All healthy → everything is fine

# Other Available Operations

- View an agent's messages: `./.osc/scripts/team.sh inbox <team-id> --agent <name>`
- Send a message: `./.osc/scripts/team.sh send <team-id> --from <agent> --to <agent> --type <type> "<msg>"`
- Continuous monitoring: `./.osc/scripts/team.sh watch <team-id>`
- Stop team: use `team-stop` skill
