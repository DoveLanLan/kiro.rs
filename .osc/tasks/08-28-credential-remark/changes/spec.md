# Spec: 凭据备注（remark）功能

## 数据模型

### `KiroCredentials`（src/kiro/model/credentials.rs）

新增字段，位置放在 `email` 字段附近：

```rust
/// 用户自定义备注（用于区分不同账号，可选）
#[serde(skip_serializing_if = "Option::is_none")]
pub remark: Option<String>,
```

注意：`impl KiroCredentials` 中的 `Default` derive 自动覆盖；`credentials.rs` 中 3 处手工构造全部字段的测试（`test_to_json`、`test_region_field_serialization`、`test_region_field_none_not_serialized`、`test_region_roundtrip`）需要补 `remark: None`。

### `CredentialEntrySnapshot`（src/kiro/token_manager.rs:521）

```rust
/// 用户自定义备注（用于前端显示）
#[serde(skip_serializing_if = "Option::is_none")]
pub remark: Option<String>,
```

快照构造处（token_manager.rs:1476 附近）从 `e.credentials.remark.clone()` 填充。

### `CredentialStatusItem`（src/admin/types.rs:24）

```rust
/// 用户自定义备注（用于前端显示）
#[serde(skip_serializing_if = "Option::is_none")]
pub remark: Option<String>,
```

`AdminService::get_all_credentials` 映射处补 `remark: entry.remark`。

### 请求类型（src/admin/types.rs）

```rust
/// 修改备注请求
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SetRemarkRequest {
    /// 新备注内容（空字符串表示清除备注）
    pub remark: String,
}
```

空字符串规范化：后端在 `set_remark` 中将 trim 后为空的值存为 `None`，避免文件中出现 `"remark": ""`。

## TokenManager（src/kiro/token_manager.rs）

### set_remark（仿照 set_priority，无 select_highest_priority）

```rust
pub fn set_remark(&self, id: u64, remark: String) -> anyhow::Result<()>
```

- 锁内找到 entry，`entry.credentials.remark = 规范化后的值`
- 调用 `self.persist_credentials()?` 回写
- 语义：与 set_priority 一致，持久化失败返回 Err 但内存已生效

### 日志 label helper（模块级 pub 函数）

```rust
pub fn credential_label(id: u64, remark: Option<&str>) -> String {
    match remark {
        Some(r) if !r.trim().is_empty() => format!("#{}[{}]", id, r.trim()),
        _ => format!("#{}", id),
    }
}
```

## Admin 层（src/admin/）

- `service.rs`：`pub fn set_remark(&self, id: u64, remark: String) -> Result<(), AdminServiceError>`，走 `classify_error` 分类（与 set_priority 相同模式）
- `handlers.rs`：`set_credential_remark` handler，成功返回 `凭据 #{} 备注已更新`
- `router.rs`：`.route("/credentials/{id}/remark", post(set_credential_remark))`，并更新路由文档注释

## 日志替换（全量 34 处 `凭据 #{}`）

替换规则：`凭据 #{id}` → `凭据 {}` + `credential_label(id, remark)`。

各场景 remark 来源：
- `token_manager.rs` 内部：同一作用域内有 entry/credentials 时取 `entry.credentials.remark.as_deref()`；仅有 `id` 的分支（如 select/切换逻辑）从 `self.entries` 查询，若无则用 helper 的退化分支
- `provider.rs`（CallContext）：`ctx.credentials.remark.as_deref()`
- `admin/handlers.rs`、`admin/service.rs`：这些是操作反馈消息（HTTP 响应），保持 `#{id}` 不变 —— 用户在界面上操作，界面本身已显示备注

## Admin UI

### types/api.ts

- `CredentialStatusItem` 增加 `remark?: string`
- 新增 `SetRemarkRequest { remark: string }`

### api/credentials.ts

```ts
export async function setCredentialRemark(id: number, remark: string): Promise<SuccessResponse>
```

POST `/credentials/${id}/remark`。

### hooks/use-credentials.ts

新增 `useSetRemark`，仿照 `useSetPriority`。

### components/credential-card.tsx

- 卡片头部（标题区）在 `#id` 旁显示 remark（Badge 或灰字）
- 行内编辑：复用优先级的编辑交互（点击铅笔/文本 → Input + 确认），空值提交表示清除
- 编辑成功后 invalidate credentials 查询（react-query 缓存刷新）

## 测试

Rust 单测（credentials.rs / token_manager.rs）：
1. `remark` 字段解析：JSON 含/不含 remark
2. 序列化：有 remark 时输出 `"remark"`；None 时不输出
3. roundtrip 一致性
4. `credential_label`：有备注 / 空白备注 / 无备注三种分支
5. `set_remark`：设置、清除（空串 → None）、凭据不存在报错

前端不加自动化测试（项目现状无前端测试设施），手动验证。

## 回归清单

- [ ] 旧格式 credentials.json（无 remark）正常加载
- [ ] 修改备注后 credentials.json 被正确回写（多凭据格式）
- [ ] 单凭据（对象格式）设置备注不报错（不回写文件，内存生效）
- [ ] 修改备注不影响优先级排序与当前凭据选择
- [ ] 备注修改后日志立即反映新值（下次打印时）
- [ ] admin-ui 构建通过（pnpm build）
- [ ] cargo build + cargo test 通过
