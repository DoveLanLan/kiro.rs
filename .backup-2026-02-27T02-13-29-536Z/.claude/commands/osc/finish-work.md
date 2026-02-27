# /osc:finish-work

收尾清单（建议在提交/PR 前运行）：

1) 更新变更文档：`.osc/changes/<date>-<slug>/change-summary.md`
2) 运行质量门禁：按 `.osc/quality-gate.md` 执行
3) 记录会话：`/osc:record-session`
4) 标记任务完成：运行 `./.osc/scripts/task.sh done`（自动更新 task.json status → done，记录 progress.log，提示分支合并）
5) 提交代码：确保所有改动已 commit，edit counter 会自动重置

注意：步骤 4 会自动处理分支提示，如果当前在任务分支上会提示合并或推送。
