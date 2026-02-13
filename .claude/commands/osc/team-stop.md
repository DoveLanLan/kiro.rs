# /osc:team-stop

目标：优雅停止一个运行中的团队。

## 立即执行

1) 列出运行中的团队：`./.osc/scripts/team.sh list`
2) 确认用户要停止的团队（如果只有一个直接停止）。
3) 停止团队：
   ```bash
   ./.osc/scripts/team.sh stop <team-id>
   ```
4) 显示停止结果。

## 停止流程

团队使用优雅 shutdown：
1. 写 `.shutdown` 信号文件，通知 agent 完成当前操作
2. 等待 30 秒 grace period
3. 发送 SIGTERM
4. 再等 10 秒
5. 最后 SIGKILL

## 注意

- 停止后团队状态变为 `stopped`，agent 的 worktree 仍保留
- 如需清理 worktree：`./.osc/scripts/multi-agent/cleanup.sh <worktree-path>`
