# Proposal: 凭据备注（remark）功能

## 背景

多凭据用户无法区分凭据对应的真实账号。现有的 `email` 字段是自动从 Kiro API 获取的，存在两个问题：
- 未必总能获取到（为空）
- 多个凭据可能是同一个邮箱（不同 refreshToken 的场景）

用户需要一个自由文本备注字段，手动标注"这是哪个账号"。

## 目标

1. 凭据支持可选的 `remark` 字段，持久化到 `credentials.json`（camelCase 序列化）
2. Admin API 支持：状态列表返回 `remark`、新增 `POST /credentials/:id/remark` 修改接口
3. Admin UI：凭据卡片显示备注，支持行内编辑（复用优先级的行内编辑交互模式）
4. 运行日志：凭据相关日志由 `凭据 #2` 变为 `凭据 #2[工作号]` 格式，排障时可直接识别账号

## 非目标

- 不在"添加凭据"表单中提供备注输入（用户明确只要求列表编辑）
- 不改动单凭据（旧格式）的行为差异 —— 字段同样支持，只是单凭据格式不回写文件
- 不做备注搜索/过滤

## 方案

字段命名：`remark`（JSON 字段 `"remark"`，Rust 字段 `remark: Option<String>`）。

日志显示格式：`#{id}[{remark}]`，无备注时退化为 `#{id}`，通过公共 helper 函数统一生成。

## 兼容性

- 旧 `credentials.json` 无 `remark` 字段 → serde `Option` 默认 None，完全兼容
- 序列化时 `skip_serializing_if = "Option::is_none"`，不污染无备注用户的文件
- 前端旧版本读到新字段不受影响（多余 JSON 字段被忽略）
