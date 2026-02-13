# /osc:start

目标：在开始写代码前，把工作流与上下文固化为“可审计的落盘文档”，并按步骤推进。

## 立即执行（按顺序）

1) 读取 `.osc/workflow.md` 与 `.osc/spec/*/index.md`（如果索引为空，先补齐链接/约定）。
2) 如果仓库还没有项目规范：运行 `project-spec`，写入 `.osc/spec/project-spec.md`。
3) 如果这是一次变更：运行 `change-workflow`，写入 `.osc/changes/<YYYY-MM-DD>-<slug>/` 的 proposal/spec/tasks。
4) 如果用户明确要求实现：按 `tasks.md` 逐条实施。
5) 收尾：运行 `quality-gate`，写入 `.osc/quality-gate.md`。

## 重要规则

- 产物必须写入对应 `.md` 文件（不要只在聊天里输出）。
- 小步提交，避免 scope creep。
