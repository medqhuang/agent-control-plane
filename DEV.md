# DEV

这份文档只服务两件事：

- 让维护者快速理解当前架构与阶段边界
- 让总控可以按阶段给 agent 派发明确任务

## 项目定义

这是一个面向远程 AI 编码 CLI 的控制平面。

核心目标：

- 统一监控多个 remote 上的多个 agent session
- 统一接收 approval request
- 统一在本地 `approve / reject`

平台边界：

- 本地开发：Windows
- 本地目标：Windows + macOS
- 远程 provider：Linux

硬约束：

- `relay` 负责本地聚合状态与 approval 一致性
- approval 必须用 `request_id`
- session 事件必须带顺序信息
- 超时只能 `reject` 或 `expire`
- 核心层不能写死 Windows 路径、PowerShell、Windows/macOS 平台 API

## 当前阶段

当前项目状态：

- 已完成：`P0`、`P1`、`P1.5`、`P2`、`P2.5`、`P3`
- 当前阶段：`P4 Remote-Agent Foundation`
- `V1` 暂不接入 `Claude Code`

当前主线不是继续打磨旧 bridge，而是把远端执行边界迁到 `remote-agent`。

## 当前稳定基线

进入 `P4` 前，下面这些能力和规则已视为冻结基线：

### Relay 基线

- `GET /v1/snapshot`
- `POST /v1/approval-response`
- in-memory `session store`
- in-memory `approval store`
- 最小 `event log`
- approval 幂等保护
- approval / session 状态一致性

### Desktop 基线

- `desktop/` 最小可启动骨架
- `Electron + Node.js + 原生 HTML/CSS/JS`
- 单 relay `snapshot` 读取
- session 列表
- pending approvals 列表
- 本地 `approve / reject` 提交
- relay 连接状态展示

### 冻结规则

- `approved -> session=running`
- 相同决策重复提交：成功返回，但不重复写事件
- 冲突决策重复提交：返回 `409`
- relay 仍然是本地聚合真源
- 先 provider writeback 成功，再提交本地状态
- 本地控制端当前保持单 relay MVP

### 旧 Kimi bridge 的现状

旧 Kimi bridge 仍保留验证价值，但不再作为长期架构继续扩展：

- `request_id` 仍是 adapter 派生
- writeback 仍依赖 `tmux` 与当前 TUI 布局
- relay 仍是 in-memory
- 这条链路已经完成验证任务，但不应再作为 `P4+` 主路径

## 架构迁移方向

`P3` 前的基线链路：

```text
desktop -> relay -> local kimi bridge -> WSL / SSH / tmux / TUI
```

`P4` 开始的目标链路：

```text
desktop -> relay -> remote-agent -> provider native interface
```

provider 原生接入策略固定为：

- `Kimi`：`kimi --wire`
- `Codex`：`codex app-server`
- `Claude Code`：后移到 `V2`

## 阶段总览

- `已完成`：`P0` 项目初始化
- `已完成`：`P1` Relay Core
- `已完成`：`P1.5` Relay 收口
- `已完成`：`P2` Kimi 闭环
- `已完成`：`P2.5` Kimi bridge 收口
- `已完成`：`P3` 本地控制端 MVP
- `当前`：`P4` Remote-Agent Foundation
- `后续`：`P5` Multi-Remote
- `后续`：`P6` 跨平台清理
- `后续`：`P7` Codex Support
- `后续`：`P8` 可靠性增强
- `V2`：`Claude Code Support`

## P4 Remote-Agent Foundation

### 目标

建立远端原生执行层，把 provider 运行、approval 检测、approval writeback 从本地桥接链路迁到远端 Linux。

### 当前推荐实现

- 每台远端服务器一个 `remote-agent`
- 先只支持 `Kimi`
- 远端部署优先使用 `systemctl --user`
- 用户交互优先采用“远端命令行启动 + 本地审批”模式

目标使用方式：

```bash
remote-agent serve
remote-agent kimi start --task "重构 auth 模块"
```

本地控制端继续负责：

- 看 session
- 看 approvals
- `approve / reject`

### P4 做什么

- 新建 `remote-agent/`
- 实现远端 supervisor
- 实现 `Kimi` worker
- 用 `kimi --wire` 托管 session
- 把 approval request 和状态送回 relay
- 接收 relay 的 decision 并回写给 Kimi

### P4 不做什么

- Multi-Remote
- Claude
- Codex
- tray/menu bar
- 持久化重构
- 本地 UI 启动远端 session

### P4 完成标准

- 远端 `remote-agent` 可以通过 `systemctl --user` 启动
- 可以执行 `remote-agent kimi start --task "..."`
- relay 能看到新 session 和 pending approval
- 本地审批后远端 session 能继续执行
- 本地主链路不再依赖 `WSL -> SSH -> tmux -> TUI`

## P5 Multi-Remote

### 目标

从单 remote 控制台升级为多 remote 聚合。

### 做什么

- server registry
- 多个 `remote-agent` endpoint
- 聚合多个 snapshot
- 标记 disconnected 状态

### 完成标准

- 两台远端服务器可同时显示在一个本地控制端中

## P6 跨平台清理

### 目标

把核心层整理成真正可迁移到 macOS 的结构。

### 做什么

- 清理 Windows 硬编码
- 清理 PowerShell 假设
- 抽离平台通知、托盘、菜单栏逻辑
- 明确编码、换行、路径策略

### 完成标准

- 核心层不依赖 Windows 专属能力
- 本地控制端迁移到 macOS 不需要重写底座

## P7 Codex Support

### 目标

接入第二个正式 provider。

### 推荐原生接入方式

- `codex app-server`

### 做什么

- Codex adapter
- session / approval 映射
- 本地控制端兼容 Codex session

### 完成标准

- Codex session 能通过 `remote-agent` 启动并被本地控制端监控

## P8 可靠性增强

### 目标

让系统具备日常使用可信度。

### 做什么

- reconnect
- heartbeat timeout
- stale request 保护
- 更清晰的日志
- 最小持久化
- remote-agent 重启恢复

### 完成标准

- 远端 agent 重启后状态不乱
- 重复审批无副作用
- 断线不会错误放行

## V2 Claude Code Support

`Claude Code` 已明确后移到 `V2`。

原因：

- 当前 `V1` 更需要先收稳 `remote-agent` 与 `Multi-Remote`
- `Kimi` 与 `Codex` 更适合当前控制平面主线
- `Claude Code` 的最佳接入面更偏 `CLI/SDK + hooks`，适合作为第二阶段扩展

## Agent 分配建议

当前推荐规则：

- `P0-P3`：已完成
- `P4`：`单 agent 串行`
- `P5`：`谨慎双 agent 并行`
- `P6`：`单 agent 串行`
- `P7`：`单 agent 串行`
- `P8`：可按模块边界并行
- `V2 Claude`：待 `V1` 稳定后再拆

当前不建议的分配方式：

- 一次同时推进 `P4 remote-agent` 和 `P5 Multi-Remote`
- 一次同时推进 `Kimi`、`Codex`、`Claude`
- 一边做 `remote-agent` 一边重写 desktop

## 给 Agent 的任务模板

推荐模板：

```text
当前阶段：P4 Remote-Agent Foundation

当前目标：
实现 remote-agent 的最小可运行骨架，并支持 Kimi session 启动。

这次只做：
- remote-agent supervisor 骨架
- systemd --user service 模板
- `remote-agent serve`
- `remote-agent kimi start --task "..."`

这次不要做：
- Multi-Remote
- Claude
- Codex
- desktop 重构
- relay 重构

允许修改：
- remote-agent/
- 可选：README.md、DEV.md、当日日志

完成标准：
- 远端可启动 remote-agent
- 告诉我如何验证 `remote-agent kimi start --task "..."`
```

## 当前常用命令

### 运行 relay

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane
.venv\Scripts\Activate.ps1
python -m uvicorn relay.main:app --reload
```

### 运行 desktop

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane\desktop
npm start
```

### 当前远端部署策略

`P4` 默认采用：

- `systemctl --user`

后续如果需要兼容更多环境，再补 fallback。

## 一句话收尾

`P0-P3` 已完成。当前只推进 `P4 Remote-Agent Foundation`，不要顺手回退 relay、desktop MVP 和 approval 一致性规则。
