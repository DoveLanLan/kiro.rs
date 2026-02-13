# /osc:team-create

目标：为当前任务创建一个多 agent 协作团队。

## 立即执行

1) 读取当前任务：`./.osc/scripts/task.sh status`，确认有活跃任务。
2) 列出可用模板：`ls .osc/team-templates/`，向用户展示选项。
3) 用户确认后，创建团队：
   ```bash
   ./.osc/scripts/team.sh create <task-dir> --template <template-name>
   ```
4) 显示创建结果，包括 team-id、roles 列表。
5) 提示用户：可以用 `/osc:team-start` 启动团队。

## 可用模板

- `feature-team`：plan → implement → check（标准功能开发）
- `bugfix-team`：debug → implement → check（Bug 修复）

## 注意

- 如果没有活跃任务，先引导用户创建：`./.osc/scripts/task.sh create "<title>"`
- 依赖 `jq`
