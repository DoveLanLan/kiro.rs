# Regression Checklist: 凭据备注（remark）功能

构建时间：2026-08-28

## 自动化验证

- [x] `cargo build`（debug）通过
- [x] `cargo test`：217 通过 / 8 失败 —— 8 个失败为 `anthropic::converter` 中
  `claude-sonnet-4` 等旧模型映射的遗留基线问题（已通过 git stash 在干净 master 上复现，
  与本次改动无关，上一个任务的 quality-gate.md 亦有记录）
- [x] 新增 remark 相关单测 10/10 通过（解析/序列化/roundtrip/空白规范化/持久化回写）
- [x] `admin-ui pnpm build`（tsc -b && vite build）通过
- [x] `cargo build --release` 通过（1m 12s，exit 0）

## 逐项回归

- [x] 旧格式 credentials.json（无 remark）正常加载 —— 单测
      `test_remark_field_missing_backward_compat` 覆盖 serde 解析路径
- [x] 修改备注后 credentials.json 正确回写（多凭据格式）—— 单测
      `test_set_remark_persists_and_normalizes` 断言文件内容含 `"remark"` 与备注值
- [x] 单凭据（对象格式）设置备注不报错 —— `set_remark` 不依赖回写结果
      （`persist_credentials` 对单凭据格式返回 `Ok(false)` 跳过写入，内存生效）
- [x] 修改备注不影响优先级排序与当前凭据选择 —— `set_remark` 未调用
      `select_highest_priority`，仅改写 `entry.credentials.remark`
- [x] 日志反映备注 —— token_manager.rs 与 provider.rs 中全部 25 处
      `凭据 #{}` 运行日志改为 `credential_label` 输出；保留 3 处
      （凭据不存在的错误消息 2 处 + Admin 操作反馈消息）按 spec 设计保留 `#id`
- [x] 空/空白备注规范化为 None，文件中不会出现 `"remark": ""` —— 后端
      `set_remark` trim 后判空 + 单测覆盖

## 手动验证（建议，需要运行环境）

- [ ] Web 管理面板：凭据卡片显示备注、点击"未设置/备注值"行内编辑、Enter 确认、Esc 取消
- [ ] 清空备注提交后卡片恢复"未设置"且 credentials.json 中 remark 键消失
- [ ] 日志输出形如 `已切换到凭据 #2[工作号]（优先级 0）`

## 基线说明

- 仓库存在既有的 `cargo fmt` 漂移与上述 8 个遗留测试失败，本次未触碰相关文件
  （`git diff --stat` 仅含 credentials.rs / token_manager.rs / provider.rs /
  admin/{types,service,handlers,router}.rs 与 admin-ui 前端 4 个文件）
