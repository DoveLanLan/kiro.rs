# /osc:team-dashboard

目标：查看团队的综合状态面板。

## 立即执行

1) 列出团队：`./.osc/scripts/team.sh list`
2) 显示 dashboard：
   ```bash
   ./.osc/scripts/team.sh dashboard <team-id>
   ```
3) 显示健康状态：
   ```bash
   ./.osc/scripts/team.sh health <team-id>
   ```
4) 根据状态给出建议：
   - 有 dead agent → 建议 `./.osc/scripts/team.sh restart <team-id> <agent>`
   - 有 stale agent → 建议检查或等待
   - 有 scope 冲突 → 提醒用户注意合并
   - 全部 healthy → 一切正常

## 其他可用操作

- 查看某个 agent 的消息：`./.osc/scripts/team.sh inbox <team-id> --agent <name>`
- 发送消息：`./.osc/scripts/team.sh send <team-id> --from <agent> --to <agent> --type <type> "<msg>"`
- 持续监控：`./.osc/scripts/team.sh watch <team-id>`
- 停止团队：`/osc:team-stop`
