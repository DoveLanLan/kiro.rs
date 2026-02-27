# /osc:check-frontend

检查前端质量门禁（按仓库证据优先）：

1) lint/format
2) typecheck
3) unit/integration tests
4) build

产物写入：`.osc/quality-gate.md`（由 `quality-gate` skill 生成）。
