# /osc:record-session

把本次会话的“结论/决策/下一步/风险/回滚点”整理为摘要，并写入 `.osc/workspace/<user>/journal-N.md`，并更新 `.osc/workspace/<user>/index.md`。

提示：
- `<user>` 使用 `OPEN_SPEC_CODE_USER`（在 `.claude/settings.local.json` 中设置）。
- 如果你不确定 N，请读取 `.osc/workspace/<user>/` 下现有的 `journal-*.md`，选择下一个数字。

