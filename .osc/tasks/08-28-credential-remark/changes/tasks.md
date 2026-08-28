# Tasks: 凭据备注（remark）功能

## 后端

- [x] T1 `src/kiro/model/credentials.rs`：`KiroCredentials` 增加 `remark` 字段 + 修复手工构造的测试 + 新增解析/序列化/roundtrip 单测
- [x] T2 `src/kiro/token_manager.rs`：`CredentialEntrySnapshot` 增加 `remark`、快照构造填充、`credential_label` helper 及单测
- [x] T3 `src/kiro/token_manager.rs`：`set_remark` 方法（含空串规范化 → None）+ 单测
- [x] T4 日志替换：token_manager.rs 内部日志（切换/禁用/刷新失败/成功统计等）改用 `credential_label`
- [x] T5 日志替换：provider.rs 中 CallContext 相关日志改用 `credential_label(ctx.id, ctx.credentials.remark...)`
- [x] T6 `src/admin/types.rs`：`CredentialStatusItem.remark` + `SetRemarkRequest`
- [x] T7 `src/admin/service.rs`：`set_remark` + `get_all_credentials` 映射 remark
- [x] T8 `src/admin/handlers.rs` + `router.rs`：handler + 路由 `POST /credentials/{id}/remark`

## 前端

- [x] T9 `admin-ui/src/types/api.ts`：`CredentialStatusItem.remark` + `SetRemarkRequest`
- [x] T10 `admin-ui/src/api/credentials.ts`：`setCredentialRemark`
- [x] T11 `admin-ui/src/hooks/use-credentials.ts`：`useSetRemark`
- [x] T12 `admin-ui/src/components/credential-card.tsx`：备注显示 + 行内编辑

## 收尾

- [x] T13 `cargo build --release` + `cargo test` 通过
- [x] T14 `admin-ui && pnpm build` 通过
- [x] T15 回归清单逐项确认（见 spec.md），填写 regression-checklist.md
