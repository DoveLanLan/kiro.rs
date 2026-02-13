---
name: team-create
description: 为当前任务创建一个多 agent 协作团队，选择模板后自动生成 team 配置。
---

# When to Use

When the user wants to create a multi-agent team for the current task. Requires an active task created via `./.osc/scripts/task.sh`.

# Steps

1) Read current task status:
   ```bash
   ./.osc/scripts/task.sh status
   ```
   Confirm there is an active task. If not, guide the user to create one first:
   ```bash
   ./.osc/scripts/task.sh create "<title>"
   ```

2) List available templates:
   ```bash
   ls .osc/team-templates/
   ```
   Show the user the options:
   - `feature-team`: plan → implement → check (standard feature development)
   - `bugfix-team`: debug → implement → check (bug fix)

3) After user confirms, create the team:
   ```bash
   ./.osc/scripts/team.sh create <task-dir> --template <template-name>
   ```

4) Show the result including team-id and roles list.

5) Tell the user they can start the team with the `team-start` skill.
