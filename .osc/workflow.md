# Osc workflow (open-spec-code)

这套流程用于在 Claude Code（可自动注入上下文）与 Codex CLI（以文件为准）中，把“要做什么/怎么做/做到了吗”固化为可审计的 Markdown 产物与脚本状态。

原则：
- Teach once, apply forever：把会重复出现的规则写进 `.osc/spec/`。
- Write before code：任何实际改动先产出 proposal/spec/tasks，再开始修改代码。
- Quality gates：收尾必须过门禁；失败先修再继续。

## 目录约定

- `.osc/spec/`：Living docs（长期演进的规范与决策）
- `.osc/workspace/<user>/`：个人工作区（会话记录/临时思考/草稿）
- `.osc/tasks/`：任务目录（task.json + prd/info + agent contexts）
- `.osc/scripts/`：工具脚本（developer/context/task/session/worktree/multi-agent）
- `.osc/changes/<date>-<slug>/`：一次变更的 proposal/spec/tasks + 总结/回归/回滚（由 `change-workflow` skill 落盘）

## 快速开始

```bash
open-spec-code init -u your-name
```

然后在 Claude Code 中运行：
- `/osc:onboard`
- `/osc:start`

## 会话开始（Claude Code）

启动会话时，`.claude/hooks/session-start.py` 会注入：
- 当前状态（调用 `.osc/scripts/get-context.sh`）
- `.osc/workflow.md`
- `.osc/spec/*/index.md`
- `/osc:start` 指令

## 用户标识（会话持久化）

`open-spec-code init -u <name>` 会写入 `.claude/settings.local.json` 中的环境变量：

- `OPEN_SPEC_CODE_USER=<name>`

Claude Code hooks 与脚本会读取该变量（或 `.osc/.developer`），把你定位到 `.osc/workspace/<name>/`。

## 脚本入口（可选）

- 初始化身份：`./.osc/scripts/init-developer.sh <name>`
- 当前上下文：`./.osc/scripts/get-context.sh`（或 `--json`）
- 管理任务：`./.osc/scripts/task.sh ...`
- 记录会话：`./.osc/scripts/add-session.sh --title "..." --commit <sha>`
- 并行 worktree：`./.osc/scripts/multi-agent/start.sh <task-dir>`
