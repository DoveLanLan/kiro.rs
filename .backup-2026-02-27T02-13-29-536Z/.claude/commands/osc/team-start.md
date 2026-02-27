# /osc:team-start

目标：启动一个已创建的团队，在 git worktree 中启动各 agent 进程。

## 立即执行

1) 列出已有团队：`./.osc/scripts/team.sh list`
2) 如果只有一个团队，直接启动；多个则让用户选择。
3) 启动团队：
   ```bash
   ./.osc/scripts/team.sh start <team-id>
   ```
   runtime 会自动检测（Claude Code 环境下为 claude，Codex 环境下为 codex）。
4) 显示启动结果（各 agent 的 pid 和 worktree 路径）。
5) 提示用户：可以用 `/osc:team-dashboard` 查看进度。

## 注意

- 团队按 phase 顺序启动 agent（phase 1 先启动，后续 phase 等前置完成后启动）
- 如果没有已创建的团队，引导用户先用 `/osc:team-create` 创建
