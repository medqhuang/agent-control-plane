# DEV

本文件用于维护者协作与阶段执行控制。

目标有两项：

- 使维护者能够快速理解当前架构、边界与阶段状态
- 使总控能够按照统一口径向执行 agent 派发任务并进行验收

## 项目定义

本项目是一个面向远程 AI 编码 CLI 的控制平面。

核心目标：

- 统一监控多个 remote 上的多个 agent session
- 统一接收 approval request
- 统一在本地执行 `approve / reject`

平台边界：

- 本地开发平台：Windows
- 本地目标平台：Windows 与 macOS
- 远程 provider 平台：Linux

## 全局约束

- `relay` 负责本地聚合状态与 approval 一致性
- approval 必须使用 `request_id`
- session 事件必须带顺序信息
- 超时只能进入 `reject` 或 `expire`
- 核心层不得写死 Windows 路径、PowerShell 或 Windows/macOS 专属 API
- 本地控制端不是远端 session 的生存依赖
- 远端 `remote-agent` 必须作为托管 session 的真实运行宿主
- 本地控制端关闭后，远端 session 应继续运行；本地恢复后应支持重新连接
- `remote-agent` 被终止后，优先保证“服务复活 + 控制面状态恢复”，而不是笼统承诺 provider 执行现场完整恢复

## 当前阶段

当前项目状态：

- 已完成：`P0`、`P1`、`P1.5`、`P2`、`P2.5`、`P3`
- 当前阶段：`P4 Remote-Agent Foundation`
- 下一阶段：`P4.5 Hosted Session Usability`
- `V1` 暂不接入 `Claude Code`

当前主线不是继续扩展旧 bridge，而是先完成 `P4` 的远端执行边界迁移，再进入 `P4.5` 补齐托管 session 的可用性闭环。

## 当前稳定基线

进入 `P4` 之前，以下能力与规则视为冻结基线。

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
- 相同决策重复提交：成功返回，但不重复写入事件
- 冲突决策重复提交：返回 `409`
- `relay` 仍然是本地聚合真源
- 先完成 provider writeback，再提交本地状态
- 本地控制端当前保持单 relay MVP

### 旧 Kimi bridge 的定位

旧 Kimi bridge 仍保留验证价值，但不再作为长期架构继续扩展：

- `request_id` 仍为 adapter 派生
- writeback 仍依赖 `tmux` 与当前 TUI 布局
- `relay` 仍为 in-memory
- 该链路已经完成验证任务，但不应继续作为 `P4+` 主路径

## 架构迁移方向

`P3` 前的基线链路：

```text
desktop -> relay -> local kimi bridge -> WSL / SSH / tmux / TUI
```

`P4` 开始的目标链路：

```text
desktop -> relay -> remote-agent -> provider native interface
```

provider 原生接入策略固定如下：

- `Kimi`：`kimi --wire`
- `Codex`：`codex app-server`
- `Claude Code`：延期至 `V2`

## 阶段总览

- `已完成`：`P0` 项目初始化
- `已完成`：`P1` Relay Core
- `已完成`：`P1.5` Relay 收口
- `已完成`：`P2` Kimi 闭环
- `已完成`：`P2.5` Kimi bridge 收口
- `已完成`：`P3` 本地控制端 MVP
- `当前`：`P4` Remote-Agent Foundation
- `下一步`：`P4.5` Hosted Session Usability
- `后续`：`P5` Multi-Remote
- `后续`：`P6` 跨平台清理
- `后续`：`P7` Codex Support
- `后续`：`P8` 可靠性增强
- `V2`：`Claude Code Support`

## P4 Remote-Agent Foundation

### 目标

建立远端原生执行层，将 provider 运行、approval 检测与 approval writeback 从本地桥接链路迁移到远端 Linux。

### 当前推荐实现

- 每台远端服务器一个 `remote-agent`
- 首批仅支持 `Kimi`
- 远端部署优先采用 `systemctl --user`
- 用户交互优先采用“远端命令行启动 + 本地审批”模式
- 从设计上确保远端 session 不依赖本地控制端进程存活

目标使用方式：

```bash
remote-agent serve
remote-agent kimi start --task "重构 auth 模块"
```

本地控制端继续负责：

- 查看 session
- 查看 approvals
- 执行 `approve / reject`

### 范围

`P4` 包含：

- 新建 `remote-agent/`
- 实现远端 supervisor
- 实现 `Kimi` worker
- 用 `kimi --wire` 托管 session
- 为后续 relay integration 预留稳定接口

`P4` 不包含：

- Multi-Remote
- Claude
- Codex
- tray/menu bar
- 持久化重构
- 本地 UI 启动远端 session

### 完成标准

- 远端 `remote-agent` 可以通过 `systemctl --user` 启动
- 可以执行 `remote-agent kimi start --task "..."`
- 远端最小 HTTP 服务可用
- `Kimi --wire` 最小 worker 骨架可运行
- 本地主链路开始脱离 `WSL -> SSH -> tmux -> TUI`

### 方向性要求

`P4` 需要先把语义定死，但不要求一次完成全部恢复能力：

- 远端 session 的生命周期不能绑定到本地控制端
- `remote-agent` 需要成为远端 session 的真实宿主
- 后续重连恢复将作为 `P8` 的正式收口项
- `remote-agent` 被终止后的恢复语义必须先写清楚：优先恢复服务与控制面，再按 provider 能力决定是否支持 `resume / reattach`

## P4.5 Hosted Session Usability

### 目标

将托管 session 从“已经具备 foundation”补到“可以日常使用”的最小闭环。

### 阶段定位

`P4.5` 不是新架构阶段，也不是多 remote 阶段。

其职责只有一个：

- 将单 remote、单 provider 的托管 session 补成“真实可操作”的日常使用闭环

在完成 `P4.5` 之前，不进入 `P5 Multi-Remote`。

### 设立原因

当前 `P4` 的重点是远端执行边界迁移，本身仍在进行中。

`P4.5` 仅承接那些不应再塞回 `P4`，但又不能直接跳到 `P5 Multi-Remote` 的工作：

- `remote-agent -> relay` 的真实状态与 approval 闭环
- 最小 session CLI 可用性
- 托管 session 的后续交互入口
- 最小恢复契约

### 子目标

建议按以下 4 个子目标推进。

#### P4.5-A Relay Integration

目标：

- `remote-agent` 能将 session 状态、approval request 与关键生命周期事件真实送回 `relay`

最小交付：

- session 创建后可在 `relay` 中出现
- approval request 可在本地控制端出现
- `approve / reject` 可从 `relay` 回到 `remote-agent`

#### P4.5-B Session CLI

目标：

- 用户在远端 shell 中可以继续管理已托管 session，而不是只有 `start` 命令

最小交付：

- `remote-agent sessions`
- `remote-agent watch <session_id>`
- `remote-agent reply <session_id> --message "..."`
- `remote-agent stop <session_id>`

增强交付：

- `remote-agent attach <session_id>`

#### P4.5-C Hosted Session Contract

目标：

- 将“托管 session 的使用方式”定义清楚

最小交付：

- `start` 是后台托管语义，不占用当前 shell
- `watch` 是只读观察语义
- `attach` 是重新接回交互语义
- `reply` 是非 attach 模式下的追加输入语义

#### P4.5-D Recovery Contract

目标：

- 在实现前先定义恢复边界，避免夸大能力

最小交付：

- 服务复活语义
- 控制面状态恢复语义
- provider 运行时恢复边界
- “服务可复活”不等于“执行现场必然完整恢复”

### 范围

`P4.5` 包含：

- 打通 `remote-agent -> relay` 状态与 approval 回传
- 补齐最小 session CLI：
  - `remote-agent sessions`
  - `remote-agent watch <session_id>`
  - `remote-agent reply <session_id> --message "..."`
  - `remote-agent stop <session_id>`
- 视情况补齐：
  - `remote-agent attach <session_id>`
- 明确最小恢复契约：
  - 服务复活
  - 控制面状态恢复
  - provider 恢复边界

`P4.5` 不包含：

- Multi-Remote
- Codex
- Claude
- tray/menu bar
- 大规模 desktop 重构
- 完整持久化系统

### 交付物

至少应落在以下位置之一：

- `remote-agent/src/remote_agent/relay/`
- `remote-agent/src/remote_agent/supervisor/`
- `remote-agent/src/remote_agent/providers/kimi/`
- `remote-agent/README.md`
- 根目录 `DEV.md`
- 必要时新增对应阶段 worklog

### 验收标准

必须同时满足以下条件：

1. 用户执行 `remote-agent kimi start --task "..."` 后，session 能回到 `relay`
2. 本地控制端能看到该 session 与对应 approval
3. 用户可以在远端 shell 中通过 `reply` 与已托管 session 继续交互
4. 用户可以在远端 shell 中列出、观察并停止一个已托管 session
5. 文档明确写清托管语义与恢复边界

### 建议验证路径

建议至少保留一套固定验证路径：

1. 启动 `remote-agent` 服务
2. 启动一个 `Kimi` 托管 session
3. 在本地 `relay` / `desktop` 中确认 session 出现
4. 触发一次 approval 并完成本地审批
5. 在远端 shell 中使用 `sessions` / `watch` / `reply` / `stop`
6. 验证文档中的恢复边界描述与当前实现一致

### 完成标准

- `remote-agent kimi start --task "..."` 创建的 session 能回到 `relay`
- 本地控制端能看到该 session 与对应 approval
- 用户可以在远端 shell 中继续通过 session CLI 管理并回复已托管 session
- 文档与实现都明确恢复语义，不再将托管平台表述为仅“能启动”

## P5 Multi-Remote

### 目标

将单 remote 控制台升级为多 remote 聚合。

### 范围

- server registry
- 多个 `remote-agent` endpoint
- 聚合多个 snapshot
- 标记 disconnected 状态

### 完成标准

- 两台远端服务器可同时显示在一个本地控制端中

## P6 跨平台清理

### 目标

将核心层整理成真正可迁移到 macOS 的结构。

### 范围

- 清理 Windows 硬编码
- 清理 PowerShell 假设
- 抽离平台通知、托盘、菜单栏逻辑
- 明确编码、换行与路径策略

### 完成标准

- 核心层不依赖 Windows 专属能力
- 本地控制端迁移到 macOS 不需要重写底座

## P7 Codex Support

### 目标

接入第二个正式 provider。

### 推荐原生接入方式

- `codex app-server`

### 范围

- Codex adapter
- session / approval 映射
- 本地控制端兼容 Codex session

### 完成标准

- Codex session 能通过 `remote-agent` 启动并被本地控制端监控

## P8 可靠性增强

### 目标

使系统具备日常使用可信度。

### 范围

- reconnect
- heartbeat timeout
- stale request 保护
- 更清晰的日志
- 最小持久化
- `remote-agent` 重启恢复
- 本地控制端关闭后的重连恢复
- 重新枚举 active sessions 与 pending approvals
- 明确区分：
  - 控制平面状态恢复
  - provider session 重新接管
  - provider 原始执行现场恢复

### 完成标准

- 远端 agent 重启后状态不乱
- 重复审批无副作用
- 断线不会错误放行
- 本地控制端关闭后重新打开，仍可恢复远端 active sessions 与 pending approvals 视图
- 文档与实现都明确说明：服务可复活不等于 provider 执行现场一定完整恢复

## V2 Claude Code Support

`Claude Code` 已明确后移到 `V2`。

原因如下：

- `V1` 更需要先收稳 `remote-agent` 与 `Multi-Remote`
- `Kimi` 与 `Codex` 更适合当前控制平面主线
- `Claude Code` 的最佳接入面更偏 `CLI / SDK + hooks`，适合作为第二阶段扩展

## Agent 分配建议

当前推荐规则：

- `P0-P3`：已完成
- `P4`：`单 agent 串行`
- `P4.5`：`单 agent 串行`
- `P5`：`谨慎双 agent 并行`
- `P6`：`单 agent 串行`
- `P7`：`单 agent 串行`
- `P8`：可按模块边界并行
- `V2 Claude`：待 `V1` 稳定后再拆

当前不建议的分配方式：

- 一次同时推进 `P4 remote-agent`、`P4.5 hosted session usability` 和 `P5 Multi-Remote`
- 一次同时推进 `Kimi`、`Codex`、`Claude`
- 一边做 `remote-agent` 一边重写 desktop

`P4.5` 推荐拆法：

- 先做 `P4.5-A Relay Integration`
- 再做 `P4.5-B Session CLI`
- 再做 `P4.5-C Hosted Session Contract`
- 最后做 `P4.5-D Recovery Contract`

## Agent 任务模板

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

后续如需兼容更多环境，再补 fallback。

## 总结

`P0-P3` 已完成。当前应优先完成 `P4 Remote-Agent Foundation`，随后进入 `P4.5 Hosted Session Usability`。在此之前，不进入 `P5 Multi-Remote`，也不回退既有 `relay`、desktop MVP 和 approval 一致性规则。
