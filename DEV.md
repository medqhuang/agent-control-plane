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
- approval 对外继续使用 `request_id`，但 multi-remote 下必须结合 `remote_id` 唯一定位
- session 事件必须带顺序信息
- 超时只能进入 `reject` 或 `expire`
- 核心层不得写死 Windows 路径、PowerShell 或 Windows/macOS 专属 API
- 本地控制端不是远端 session 的生存依赖
- 远端 `remote-agent` 必须作为托管 session 的真实运行宿主
- `remote-agent` 直接连接 provider worker；`relay` 不代理 provider 原始模型数据流，只处理控制面状态、审批信令与事件转发
- 本地控制端关闭后，远端 session 应继续运行；本地恢复后应支持重新连接
- `remote-agent` 被终止后，优先保证“服务复活 + 控制面状态恢复”，而不是笼统承诺 provider 执行现场完整恢复
- 恢复能力优先建立在现有 `session registry / state store` 上扩展，不新增独立顶层架构
- 必须明确区分三层能力：服务复活、控制面状态恢复、provider 执行现场恢复；文档与实现都不能混写

## 当前阶段

当前项目状态：

- 已完成：`P0`、`P1`、`P1.5`、`P2`、`P2.5`、`P3`、`P4`、`P4.5`、`P4.5-A`、`P4.5-B`、`P4.5-C`、`P4.5-D`、`P5`、`P5-1`、`P5-1.5`、`P5-2`、`P5-3`、`P6-1`、`P6-2`、`P6-3`、`P6`、`P6.5`
- 当前阶段：`P7 Local Session Interaction UI`
- 当前子目标：`P7-B Desktop Reply Submission And Relay Session Interaction Route`
- 已完成子目标：`P7-A Desktop Session Detail And Transcript`
- `V1` 暂不接入 `Claude Code`

当前主线已完成 `P5 Multi-Remote`、`P6 跨平台清理` 与 `P6.5 Public Beta Release`
收口，当前进入 `P7 Local Session Interaction UI`。
当前阶段不以通用聊天 UI 或推理链可视化作为主目标，但本地控制端必须具备对已托管 session 的基础交互能力；这属于当前产品闭环，而不是后续可有可无的增强项。
`P6-1`、`P6-2` 与 `P6-3` 已完成；`P6` 整体已完成，阶段收口记录见 `P6_worklog.md`。
`P6.5-1 Release Surface Definition`、`P6.5-2 Desktop Delivery Baseline`、
`P6.5-3 Remote-Agent Trial Install Surface`、
`P6.5-4 Quick Start And Trial Docs`、`P6.5-5 Trial Operator Guide`、
`P6.5-6 Issue Templates And Feedback Intake` 与
`P6.5-7 Release Notes And Launch Checklist` 已完成；当前阶段前推到
`P7 Local Session Interaction UI`。

## 当前融合原则

当前阶段吸收的恢复、审批缓冲与检查点思路，必须遵循以下原则：

- 不改动既有托管平台顶层架构：`desktop -> relay -> remote-agent -> provider native interface`
- 不引入新的顶层控制面服务；状态与恢复能力在现有 `session registry / state store` 上扩展
- `remote-agent` 继续作为远端运行宿主；`relay` 继续作为本地控制面聚合层
- `relay` 不代理 provider 原始模型数据流，只维护控制面所需的状态、审批与事件回放能力
- 不在公开文档中引用泄露源码作为正式依据；仅吸收可独立成立的工程模式，如 checkpoint、approval queue、event replay 与恢复边界

## 当前阶段源码参考顺序

当前阶段允许并要求参考源码，但参考顺序必须固定，避免执行时被外部实现带偏：

1. 当前仓库源码
   - 优先阅读 `relay/`、`desktop/`、`remote-agent/`
   - 所有实现必须先适配现有托管平台链路，而不是先套外部项目结构
2. 官方公开接口与公开源码
   - `Kimi -> kimi --wire`
   - `Codex -> codex app-server`
   - `Claude Code -> CLI / SDK / hooks`
3. 本地参考源码
   - `references/claude-code-haha-main/`
   - 当前只用于参考 checkpoint、approval、bridge messaging、state restore、event replay 等实现模式
4. 其他成熟开源项目源码
   - 只用于补充结构与工程实现手法，不改变当前阶段顺序

当前阶段对 Claude Code 源码的使用边界：

- 允许将 `references/claude-code-haha-main/src/QueryEngine.ts`
  、`references/claude-code-haha-main/src/Tool.ts`
  、`references/claude-code-haha-main/src/bootstrap/state.ts`
  与 `references/claude-code-haha-main/src/bridge/` 作为 `P7` 与 `P10` 的实现参考
- 当前不因为本地已有 Claude Code 源码而提前进入 `Claude Code Support`
- 当前不因为本地已有 Claude Code 源码而改变后续 `P7 -> P8 -> P9 -> P10 -> V2 Claude` 的阶段顺序
- 当前不将 Claude 的内部实现细节直接抽象成项目的顶层架构

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
- `已完成`：`P4` Remote-Agent Foundation
- `已完成`：`P4.5` Hosted Session Usability
- `已完成`：`P4.5-A` Relay Integration
- `已完成`：`P4.5-B` Session CLI
- `已完成`：`P4.5-C` Hosted Session Contract
- `已完成`：`P4.5-D` Recovery Contract
- `已完成`：`P5` Multi-Remote
- `已完成`：`P6` 跨平台清理
- `当前`：`P7` Local Session Interaction UI
- `后续`：`P8` V1.0 Release
- `后续`：`P9` Codex Support
- `后续`：`P10` 可靠性增强
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

### 当前判断

- `P4` 已完成
- 当前不再继续向 `P4` 回填 hosted-session usability 工作

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

`P4.5` 已完成；其后续 `P5 Multi-Remote`、`P6 跨平台清理` 与 `P6.5 Public Beta Release` 也已完成，当前进入 `P7 Local Session Interaction UI`。

### 设立原因

`P4` 已完成远端执行边界迁移。

`P4.5` 仅承接那些不应再塞回 `P4`，但又不能直接跳到 `P5 Multi-Remote` 的工作：

- `remote-agent -> relay` 的真实状态与 approval 闭环
- 最小 session CLI 可用性
- 托管 session 的后续交互入口
- 最小恢复契约

### 子目标

`P4.5` 已按以下 4 个子目标完成收口。

#### P4.5-A Relay Integration

状态：

- 已完成

目标：

- `remote-agent` 能将 session 状态、approval request 与关键生命周期事件真实送回 `relay`

最小交付：

- session 创建后可在 `relay` 中出现
- approval request 可在本地控制端出现
- `approve / reject` 可从 `relay` 回到 `remote-agent`

#### P4.5-B Session CLI

状态：

- 已完成

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

状态：

- 已完成

目标：

- 将“托管 session 的使用方式”定义清楚

最小交付：

- `start` 是后台托管语义；命令本身只等待首个 checkpoint，达到“本轮完成”或“出现 approval”后返回
- `sessions` 是当前 `remote-agent` runtime 内的托管 session 列表视图
- `watch` 当前是单次读取最新状态，不是持续 follow
- `reply` 是非 `attach` 模式下的追加输入语义
- `stop` 当前终止 hosted session，并将其从当前 runtime 列表中移除
- `stop` 当前不支持在 `approval_pending` 或 turn 进行中执行
- `attach` 当前未实现，不能写成已支持

当前 contract 固定口径：

- `remote-agent kimi start --task "..."` 创建的是 hosted session；命令返回后，后续 session 生命周期由 `remote-agent serve` 托管，而不是由当前 shell 持有
- `remote-agent sessions` 只列当前 `remote-agent` 进程还在托管的 session；它不是 relay 历史视图，也不是持久化恢复视图
- `remote-agent watch <session_id>` 当前是单次读取，不负责持续流式跟随输出；如需刷新，重复执行即可
- `remote-agent reply <session_id> --message "..."` 在同一 hosted session 上追加一轮输入；它不是重新 attach TTY，也不是新的独立 session
- `remote-agent stop <session_id>` 当前只在 session 空闲时可用；若 session 正在等待审批或正在执行 turn，命令应明确拒绝
- `approval_pending` 下拒绝 `stop` 的原因是：当前实现优先保持 hosted runtime 与 `relay` 上 pending approval 语义一致，避免本地出现仍可审批、远端却已被强停的分叉状态
- `remote-agent attach <session_id>` 当前未实现；如果文档需要提到它，只能作为未来增强入口，不能写成当前可用命令

#### P4.5-D Recovery Contract

状态：

- 已完成

目标：

- 在实现前先定义恢复边界，避免夸大能力

最小交付：

- Local Desktop 断开后，远端 `remote-agent` 与 hosted session 的存活语义
- `awaiting_reconnect / online / offline` 等恢复状态约定
- 最小 checkpoint 结构约定：最近会话上下文、当前工作目录、待审批项、时间戳、客户端连接标识
- pending approvals 与控制面事件 replay 约定
- 服务复活语义
- 控制面状态恢复语义
- provider 运行时恢复边界
- “服务可复活”不等于“执行现场必然完整恢复”

当前 recovery contract 固定口径：

- Local Desktop 断开、关闭或崩溃后，只要远端 `remote-agent serve` 与其 provider 子进程仍存活，hosted session 就继续运行；Desktop 不是 session 宿主
- Local Desktop 重新打开后的当前承诺，仅是重新连接 `relay` 并读取 `relay` 当下仍持有的 snapshot；Desktop 自身不持有 hosted session，也不负责 provider 执行现场恢复
- `online / offline / awaiting_reconnect` 当前只作为目标 recovery 状态词汇存在，不是当前已经稳定暴露的 snapshot 字段；文档不能把它们写成既有 API
- 最小 checkpoint 当前是目标契约，不是现有持久化实现；后续至少应包含：最近会话上下文、当前工作目录、待审批项、时间戳、客户端连接标识
- pending approvals 当前对外继续使用 `request_id`；但在 multi-remote 下必须结合 `remote_id + request_id` 唯一定位；pending 状态目前只存在于 `relay` 内存态与 `remote-agent` 进程内存态，重启后没有自动恢复或 replay 承诺
- 控制面事件当前只保证 live 上报与顺序信息；当前没有持久化 event buffer，也没有跨重启 replay 机制
- `remote-agent` 服务复活后的当前承诺仅限于：服务可重新拉起并接受新请求；当前不承诺恢复此前 hosted session、`request_id -> session_id` 映射、pending approvals 或 provider 子进程现场
- `relay` 重启后的当前承诺仅限于：重新开始接收新的 session / approval / event；当前不承诺恢复旧 snapshot，也不承诺自动向远端补拉历史状态
- provider 子进程异常退出后的当前边界是：hosted session 可能失败或消失；当前不承诺对 provider 原始执行现场做完整 `resume / reattach`
- 当前必须避免三层能力混写：服务可复活，不等于控制面状态已恢复；控制面状态可恢复，也不等于 provider 执行现场一定完整恢复

当前阶段结论：

- `P4.5` 已完成
- `P5` 也已在此基线上完成
- 当前已实现的是：单 remote hosted-session 日常使用闭环，且已扩展到 multi-remote 聚合控制面
- 当前仍未实现的是：checkpoint 持久化、pending approvals replay、控制面事件 replay、`remote-agent` 重启恢复、provider 执行现场恢复
- 因此 `P6` 已完成，当前阶段可以进入 `P6.5`，但恢复实现仍继续保留在 `P8`

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
  - Local Desktop 断开后的 session 存活规则
  - checkpoint 保存与恢复规则
  - pending approvals 回放规则
  - 控制面事件 replay 规则
  - 服务复活
  - 控制面状态恢复
  - provider 恢复边界

`P4.5` 不包含：

- Multi-Remote
- Codex
- Claude
- 多设备切换
- 手机只读/审批端
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

### 状态

- 已完成

### 目标

将单 remote 控制台升级为多 remote 聚合。

### 已完成子目标

- `P5-1 Server Registry`
  - `relay` 内建立最小 server registry
  - snapshot 返回 `servers + sessions + approvals`
  - 单 remote 旧路径继续可用
- `P5-1.5 Approval Identity Hardening`
  - approval 内部唯一定位改为 `remote_id + request_id`
  - 仅传 `request_id` 时保留单 remote 兼容
  - 多 remote 歧义时返回明确错误
- `P5-2 Desktop Multi-Remote View`
  - desktop 消费 `snapshot.servers`
  - Remotes 面板可同时展示多个 remote
  - session / approval 列表按 `remote_id` 区分来源
  - approval 操作路径携带 `remote_id`
- `P5-3 Remote Status Marking`
  - 为 remote 增加 `connected / disconnected / unreachable` 最小状态标记
  - Remotes 面板展示该状态
  - 保持单 remote 兼容

### 当前已实现能力

- multi-remote server registry
- `remote_id` 感知的 approval identity
- desktop multi-remote 聚合视图
- `connected / disconnected / unreachable` 最小状态标记
- 单 remote 与现有 approval / session 主链路不回退

### 当前边界

- 还没有 reconnect 体系
- 还没有持久化或跨重启 snapshot rehydrate
- 还没有 pending approvals replay
- 还没有控制面事件 replay
- 还没有 provider 执行现场恢复

### 完成标准

- 两台远端服务器可同时显示在一个本地控制端中
- 同 `request_id` 在不同 remote 下不会错误命中
- desktop 能明确区分多个 remote 的 session / approval 来源
- remote 可显示最小连通状态而不引入完整 reconnect 体系

### 完成结论

`P5` 已完成，并为 `P6 跨平台清理` 提供了稳定的多 remote 基线。
`P5` 没有把 reconnect、持久化或恢复系统实现提前写成已支持能力；这些工作仍保留在 `P8`。

## P6 跨平台清理

### 状态

- 已完成
- 已完成：`P6-1 Platform Assumption Audit`
- 已完成：`P6-2 Runbook And Text Policy Cleanup`
- 已完成：`P6-3 Boundary Cleanup`

### 目标

将核心层整理成真正可迁移到 macOS 的结构。

### 范围

- 清理 Windows 硬编码
- 清理 PowerShell 假设
- 抽离平台通知、托盘、菜单栏逻辑
- 明确编码、换行与路径策略
- 在 `P6-1 / P6-2` 已完成基础上，继续 `P6-3 Boundary Cleanup`

### 完成标准

- 核心层不依赖 Windows 专属能力
- 本地控制端迁移到 macOS 不需要重写底座
- `P6-3` 继续保证 Linux deploy 壳层与 desktop 平台壳层不回流到共享核心

## P6.5 Public Beta Release

### 状态

- 已完成
- 已完成：`P6.5-1 Release Surface Definition`
- 已完成：`P6.5-2 Desktop Delivery Baseline`
- 已完成：`P6.5-3 Remote-Agent Trial Install Surface`
- 已完成：`P6.5-4 Quick Start And Trial Docs`
- 已完成：`P6.5-5 Trial Operator Guide`
- 已完成：`P6.5-6 Issue Templates And Feedback Intake`
- 已完成：`P6.5-7 Release Notes And Launch Checklist`

### 目标

在不等待 `Codex Support` 完成的前提下，发布首个公开可试用版本，用于尽早获取外部反馈。

### 定位

`P6.5` 是发布准备阶段，不是 provider 扩展阶段。

其目标是将已经完成的：

- `Kimi + remote-agent`
- hosted session CLI
- 本地审批与状态查看
- Multi-Remote
- 跨平台清理结果

封装成可以公开试用的最小 Beta 版本。

### 范围

- Desktop 最小可运行交付形态
- `remote-agent` 最小安装与启动封装
- Quick Start
- 平台支持矩阵
- 已知限制说明
- release notes
- issue 模板
- 试用讲解说明或操作脚本

### 不包含

- `Codex Support`
- `Claude Code`
- `P10` 级别的可靠性硬化
- 商业级安装器
- 多设备切换

### P6.5-1 Release Surface Definition

`P6.5-1` 的职责不是打包，而是先把第一次公开 Beta 的 release surface
定义收稳，避免后续打包、文档与对外表述继续漂移。
`P6.5-1` 已完成；`P6.5-2` 到 `P6.5-7` 也已依次完成，当前阶段前推到
`P7 Local Session Interaction UI`。

此次定义固定为：

- 面向技术试用者的 source-run / source-install Beta
- 发布单元是当前 repo 及其中的 `desktop/`、`relay/`、`remote-agent/`
- 不把尚未落地的安装器、恢复系统、额外 provider 接入写成已交付承诺

### 首次公开 Beta 包含组件

- 本地 `relay`
- 本地 `desktop`
- 远端 `remote-agent`
- `Kimi --wire`
- hosted session CLI：`start / sessions / watch / reply / stop`
- multi-remote 聚合基线

### 首次公开 Beta 不包含

- `Codex`
- `Claude Code`
- `attach`
- reconnect
- 持久化 / checkpoint / replay
- `remote-agent` 重启后托管状态恢复
- provider 执行现场恢复
- 云 relay
- desktop installer
- `remote-agent` 的 PyPI 包、wheel 或系统发行包

### 组件交付形态

- `desktop`
  - 当前交付形态是 repo 内 `desktop/` 源码目录
  - 当前启动口径是 `npm install && npm start`
  - 当前不是 installer，不承诺签名、自动更新或平台原生分发
- `remote-agent`
  - 当前交付形态是 repo 内 `remote-agent/` Python 包源码
  - 当前安装口径是从 repo 副本执行 `python -m pip install -e ./remote-agent`
    或 `bash scripts/install-systemd-user.sh --start`
  - 当前不是 PyPI 包，不承诺 apt/rpm/homebrew 之类分发面
- `relay`
  - 当前交付形态是 repo 内 `relay/` FastAPI 入口
  - 当前运行口径是用户在本地手工启动的单进程服务
  - 当前不是云服务、托管服务，也不是单独产品线

### P6.5-2 Desktop Delivery Baseline

`P6.5-2` 的职责是冻结首发公开 Beta 的 desktop 交付基线，而不是提前进入
installer、签名包或自动更新阶段。
`P6.5-2` 已完成；其后续依赖的 `P6.5-3` 到 `P6.5-7` 也已完成，当前阶段前推到
`P7 Local Session Interaction UI`。

此次冻结为：

- `desktop` 继续以 repo 内 `desktop/` 源码目录交付
- 当前桌面端启动命令固定为 `cd desktop && npm install && npm start`
- 当前 `desktop/package.json` 只暴露 `start` 与 `dev` 运行脚本；没有正式
  build / package / make 脚本
- desktop 首发公开 Beta 的本地交付平台保持为 Windows
- desktop 当前依赖一个已启动的本地 `relay`，不负责自动拉起 relay
- desktop 当前默认连接 `http://127.0.0.1:8000`，如需覆盖，使用
  `RELAY_BASE_URL`

source-run 在首发公开 Beta 中仍可接受，原因是：

- 首发试用对象是技术试用者，不是大众分发用户
- 当前更需要验证本地控制面、multi-remote 展示与 approval 流程闭环
- 现在提前承诺 installer、签名与自动更新，会把未稳定的分发面误写成已交付
- 当前 repo 已具备可重复执行的最小桌面启动路径，足以支撑公开 Beta 试用

desktop 首发公开 Beta 的不承诺项：

- installer
- `exe` / `msi` 安装包
- 代码签名
- 自动更新
- 独立桌面分发包
- 内置 relay bootstrap
- 将 Windows 之外的平台写成首发已交付

`P6.5-2` 完成后，后续 `P6.5-3` 应在此基线上继续处理远端试用安装面，而不再
回头重新定义 desktop 的首发交付形态。

### P6.5-3 Remote-Agent Trial Install Surface

`P6.5-3` 的职责是冻结首发公开 Beta 的 remote-agent 试用安装面，而不是把
当前仍需手工完成的远端配置步骤伪装成“已自动化安装”。
`P6.5-3` 已完成；后续 `P6.5-4`、`P6.5-5`、`P6.5-6` 与 `P6.5-7` 也已完成，
当前阶段前推到 `P7 Local Session Interaction UI`。

此次冻结为：

- `remote-agent` 继续以 repo 内 `remote-agent/` 源码目录交付
- 首发试用安装方式固定为：将目录复制到远端 Linux 主机后执行
  `bash scripts/install-systemd-user.sh --start`
- 首发长期运行面固定为 `systemd --user`
- provider 范围不变，仍仅覆盖 `Kimi --wire`

脚本当前已提供的安装/启动帮助：

- 创建 venv
- 从当前 workdir 执行 `python -m pip install -e`
- 写入基础 env：
  - `REMOTE_AGENT_HOST`
  - `REMOTE_AGENT_PORT`
  - `REMOTE_AGENT_LOG_LEVEL`
  - `REMOTE_AGENT_LOG_FILE`
- 渲染 `~/.config/systemd/user/remote-agent.service`
- 执行 `systemctl --user daemon-reload`
- 执行 `systemctl --user enable remote-agent.service`
- 在 `--start` 下执行 `systemctl --user restart remote-agent.service`
- 尝试确保 linger；若失败，明确报错而不是假装 logout-safe hosting 已就绪

当前仍需试用者手工完成的部分：

- 编辑 `~/.config/remote-agent/remote-agent.env`
- 补充 `REMOTE_AGENT_RELAY_ENDPOINT`
- 补充 `REMOTE_AGENT_CONTROL_BASE_URL`
- multi-remote 试用时建议补充 `REMOTE_AGENT_REMOTE_NAME`
- 确认远端到本地 relay 的可达性
- 确认本地 relay 到远端 control base URL 的可回连性
- 确认 `kimi` 已在 PATH 中，或显式提供 `KIMI_BIN`

Kimi provider binary 发现方式固定为：

- 先用命令行 `--kimi-bin`
- 再用环境变量 `KIMI_BIN`
- 最后用 PATH 中的 `kimi`
- 当前不再使用 Linux home fallback 探测 provider 二进制

最小验证命令固定为：

- `systemctl --user status remote-agent.service --no-pager`
- `remote-agent sessions`
- `remote-agent kimi start --task "..." [--kimi-bin ...]`
- `tail -n 50 ~/.local/state/remote-agent/remote-agent.log`

`P6.5-3` 完成后，后续 `P6.5-4` 应把 desktop 与 remote-agent 两侧都当作
已冻结输入，再产出完整试用路径；不再回头重定义试用安装面本身。

### relay 在首发 Beta 中的定位

- `relay` 是本地控制面的必需聚合层
- `desktop` 只消费 `relay` snapshot，不直接连远端 provider
- `remote-agent` 只向 `relay` 上报标准事件，并通过 `relay` 接收 approval
  决策回写
- 本次 Beta 不引入 hosted relay、团队共享 relay 或云端中继叙述

### 最小启动路径

1. 本地安装 `relay` 依赖并启动 `relay`
2. 本地安装 `desktop` 依赖并启动 `desktop`
3. 将 `remote-agent/` 部署到远端 Linux 主机
4. 在远端安装并启动 `remote-agent` user service
5. 手工补充远端 env 中的 `REMOTE_AGENT_RELAY_ENDPOINT`、
   `REMOTE_AGENT_CONTROL_BASE_URL` 与建议使用的 `REMOTE_AGENT_REMOTE_NAME`
6. 确认远端 `kimi --wire` 可用，或显式设置 `KIMI_BIN`
7. 在远端执行 `remote-agent kimi start --task "..."`
8. 在本地 `desktop` 中看到 session / approval，并完成一次 `approve / reject`

### 支持平台矩阵

| Surface | Platform | 首次公开 Beta 状态 | 说明 |
| --- | --- | --- | --- |
| 本地 `desktop + relay` | Windows | 支持 | 当前首发公开 Beta 的本地运行面 |
| 本地 `desktop + relay` | macOS | 不纳入首发承诺 | `P6` 已清理跨平台边界，但本次不把 macOS 写成已交付 |
| 本地 `desktop + relay` | Linux | 不包含 | 不属于当前本地目标平台 |
| 远端 `remote-agent` | Linux | 支持 | 需 `python3`、`systemd --user`、`loginctl` 与 linger |
| 远端 `remote-agent` | Windows / macOS | 不包含 | 当前没有对应 deploy 面 |
| provider | `Kimi --wire` | 支持 | 本次唯一正式 provider |
| provider | `Codex` / `Claude Code` | 不包含 | 分别后移到 `P9` 与 `V2` |

### 用户试用的最小前置条件

- 本地具备可运行 `relay` 的 Python 环境；建议按 `remote-agent` 基线统一为
  Python `3.10+`
- 本地具备 Node.js 与 npm，可在 `desktop/` 执行 `npm install`
- 远端 Linux 具备 `python3`、`venv`、`systemctl --user`、`loginctl`
- 远端用户具备 linger；若没有，需要显式执行 `loginctl enable-linger`
- 远端已安装可执行 `kimi --wire` 的 `kimi`，或能显式提供 `KIMI_BIN`
- 本地 `relay` 可被远端访问；远端 `remote-agent` 控制地址也可被本地 `relay`
  访问
- 试用者能接受当前需要手工编辑远端 env 文件，而不是完全自动安装

### 当前已知限制

- `install-systemd-user.sh` 当前不会自动写入 `REMOTE_AGENT_RELAY_ENDPOINT`、
  `REMOTE_AGENT_CONTROL_BASE_URL` 或 `REMOTE_AGENT_REMOTE_NAME`；首发 Beta
  试用仍需手工补充
- `install-systemd-user.sh` 当前只自动写基础 host / port / log env，不自动完成
  relay / control / remote-name 试用配置
- `desktop` 当前是 source-run 交付，不是安装包
- `desktop` 当前没有 build / package / installer 脚本
- `relay` 当前是本地手工启动进程，不是后台自启动服务
- `watch` 当前是单次读取，不是持续 follow
- `attach` 当前未实现
- `stop` 当前不能用于 `approval_pending` 或 turn 进行中的 session
- `relay` 与 `remote-agent` 当前都仍是内存态；重启后不会恢复既有 session、
  pending approvals 或事件视图
- 当前不承诺 provider 原始执行现场 `resume / reattach`

### P6.5-5 Trial Operator Guide

`P6.5-5` 的职责不是先做截图或路演素材，而是先给出一份可执行的小范围试用
讲解文档，让组织者能够按真实步骤带 2-5 人跑通一次试用。

`P6.5-5` 已完成；后续 `P6.5-6` 与 `P6.5-7` 也已完成，当前阶段前推到
`P7 Local Session Interaction UI`。

这一步建立在 `P6.5-4` 已完成的 Quick Start 基线上，但会进一步固定：

- 试用目标与参与角色
- 试用前准备与组织方式
- 本地 operator 的最小操作顺序
- 远端 Linux 试用者的最小操作顺序
- 一次真实 approval 演示路径
- 当任务没有触发 approval 时的换任务策略
- 常见失败点与快速排查顺序
- 试用结束后应收集的最小反馈字段

本阶段产物应优先写入 `P6.5_trial_guide.md`，并由根 `README.md`、
`desktop/README.md` 与 `remote-agent/README.md` 提供入口引用。

截图、demo capture 与路演材料当前不作为 `P6.5` 的编号阻塞项；它们可以在
后续需要对外展示时补充，但不应先于试用讲解说明。

### P6.5-6 Issue Templates And Feedback Intake

`P6.5-6` 的职责不是做正式 support 流程，而是先给第一次公开 Beta 一个最小、
统一、可回收的反馈入口，避免试用结果散落在聊天与口头记录里。

这一步建立在 `P6.5-5` 已完成的 trial guide 基线上，但会进一步固定：

- 首发 Beta 的反馈通过 repo issues 回收
- 最小模板集至少包含 bug report、trial feedback、environment / setup
- 模板字段与 `P6.5_trial_guide.md` 的反馈字段保持一致
- 反馈入口明确收集角色、平台、版本、`kimi` 发现方式、session / approval /
  `Approve` / `Reject` 结果、阻塞步骤、命令 / 日志片段与最小复现路径
- 当前入口是 Beta intake，不写成正式客服或 SLA support 流程

本阶段产物应优先落在 `.github/ISSUE_TEMPLATE/`，并由根 `README.md` 与
`P6.5_trial_guide.md` 明确说明试用后如何反馈。

### P6.5-7 Release Notes And Launch Checklist

`P6.5-7` 的职责不是继续扩张试用范围，而是把第一次公开 Beta 的对外表述与
发布前检查项收稳，确保当前版本可以被真实地、小范围地对外试用，而不夸大
功能边界。

这一步建立在 `P6.5-1` 到 `P6.5-6` 已完成的基线上，但会进一步固定：

- 一份面向外部试用者的首发 Beta release notes
- 一份面向发布前自查的 launch checklist
- release notes 中明确包含项、不包含项、平台、provider、最小试用路径、
  已知限制与反馈入口
- launch checklist 中明确发布前必须核对的文档、表述与禁说项
- 当前不把 contract-only、恢复系统、installer、`Codex` 或 `Claude Code`
  写成已支持能力

本阶段产物应优先落在 `P6.5_release_notes.md` 与
`P6.5_launch_checklist.md`，并由根 `README.md` 提供入口。

### 面向 Beta 的最小交付清单

- 一份明确写清“包含什么 / 不包含什么”的根目录 `README.md`
- 一份明确写清发布边界、平台矩阵与后续顺序的根目录 `DEV.md`
- 一份冻结 `P6.5-1`、`P6.5-2` 与 `P6.5-3` 口径的 `P6.5_worklog.md`
- 一份最小 `desktop/README.md`，明确 desktop 交付形态、启动方式与不承诺项
- 一份最小 `remote-agent/README.md`，明确试用安装面、手工步骤与最小验证命令
- 一条可操作的最小 Quick Start：本地 `relay + desktop`，远端
  `remote-agent + Kimi`
- 一份明确的支持矩阵与已知限制列表
- 一份首发试用讲解说明或操作脚本：`P6.5_trial_guide.md`
- 一组面向试用者的 issue 模板：
  `.github/ISSUE_TEMPLATE/bug_report.md`、
  `.github/ISSUE_TEMPLATE/trial_feedback.md`、
  `.github/ISSUE_TEMPLATE/environment_setup.md`
- 根 `README.md` 与 `P6.5_trial_guide.md` 中明确写出试用后反馈入口
- 一份首发 Beta release notes：`P6.5_release_notes.md`
- 一份首发 Beta launch checklist：`P6.5_launch_checklist.md`

### 建议后续子任务顺序

`P6.5` 的全部子任务已完成。当前阶段应切换到 `P7 Local Session Interaction UI`，而不是回头
继续重写 remote-agent 试用安装面。

1. `P6.5-2 Desktop Delivery Baseline`
   - 固定 desktop 首发交付形态
   - 明确 source-run 仍可接受的原因与边界
   - 不进入完整 installer
2. `P6.5-3 Remote-Agent Trial Install Surface`
   - completed
3. `P6.5-4 Quick Start And Trial Docs`
   - completed
4. `P6.5-5 Trial Operator Guide`
   - completed
5. `P6.5-6 Issue Templates And Feedback Intake`
   - completed
6. `P6.5-7 Release Notes And Launch Checklist`
   - completed

截图与 demo capture 当前仅作为后续可选辅助材料，不是 `P6.5` 的编号阻塞项。

### 完成标准

- 新用户可以按照文档完成一次本地控制端启动
- 新用户可以完成一次远端 `remote-agent` 安装与启动
- 新用户可以启动一个 `Kimi` hosted session 并完成一次本地审批
- 试用后反馈可通过统一模板回收，而不是散落在聊天里
- 对外 release notes 与发布前检查单都已经落在仓库中
- 仓库具备对外公开试用所需的最小说明、限制与反馈入口

## P7 Local Session Interaction UI

### 目标

让本地 `desktop` 成为已托管 session 的正式交互入口之一，而不再只承担状态查看和审批操作。

### 阶段定位

`P7` 是 `V1` 范围内的产品闭环阶段，不是可选增强项。

如果没有本地 UI 交互入口，`remote-agent kimi start --task "..."` 在返回 shell 后会把后续使用能力只留在远端 CLI 上，产品就无法完整承接 hosted session 的持续使用。

### 当前拆分

- `P7-A` 已完成：`Desktop Session Detail And Transcript`
- `P7-B` 当前：`Desktop Reply Submission And Relay Session Interaction Route`

### 范围

- desktop session detail 视图
- desktop 最近一轮回复或最小 transcript 展示
- desktop 对已托管 session 的 `reply` 提交
- relay 补齐本地 UI 所需的 session detail / reply 路由
- 保持远端 shell 中 `sessions / watch / reply / stop` 继续可用
- 保持 approval 仍走现有 approval 流，不重写审批语义

### 不包含

- `attach`
- 通用聊天工作台
- 推理链可视化
- 原始 token 流代理
- `Codex`
- `Claude Code`

### 完成标准

- 本地 `desktop` 可以打开某个 hosted session 的详情视图
- 本地 `desktop` 至少可以显示最近一轮回复内容或最小 transcript
- 本地 `desktop` 可以直接提交 `reply`
- 通过本地 UI 提交的 `reply` 能回到远端 hosted session 并形成下一轮结果
- 现有 remote shell CLI 与 approval 行为不回退

## P8 V1.0 Release

### 目标

以当前 `Kimi + remote-agent + Multi-Remote + Local Session Interaction UI` 为范围，完成正式 `v1.0` 发布收口。

### 范围

- 冻结 `V1` 范围与不支持项
- 收口 README、DEV、Quick Start、试用与发布文档
- 完成正式 release notes、截图、演示材料与发布检查清单
- 收口最小安装与启动路径
- 修复阻塞正式发布的高优先级缺陷
- 明确 `1.0` 已承诺能力与未承诺能力

### 不包含

- `Codex`
- `Claude Code`
- 深度恢复系统
- checkpoint / replay 全实现
- 多设备切换
- 通用聊天工作台

### 完成标准

- 新用户按文档可以完成一次本地控制端启动
- 新用户可以完成一次远端 `remote-agent` 安装与启动
- 新用户可以启动一个 `Kimi` hosted session、在本地 UI 中查看内容、提交 `reply`、并处理一次 approval
- 发布物、截图、发布说明与已知限制齐全
- 项目对外可以明确标记为 `v1.0`

## P9 Codex Support

### 目标

在 `v1.0` 之后接入第二个正式 provider。

### 推荐原生接入方式

- `codex app-server`

### 范围

- Codex adapter
- session / approval 映射
- 本地控制端兼容 Codex session

### 完成标准

- Codex session 能通过 `remote-agent` 启动并被本地控制端监控

## P10 可靠性增强

### 目标

在 `v1.0` 之后补齐更完整的恢复、checkpoint、replay 与运行时可靠性能力。

### 范围

- reconnect
- heartbeat timeout
- stale request 保护
- 更清晰的日志
- 最小持久化
- checkpoint 持久化与恢复
- pending approvals 持久化与 replay
- 控制面事件缓冲与 replay
- 高风险操作的轻量 risk scoring
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

- `V1` 更需要先收稳 `remote-agent` 与 `Multi-Remote`，并完成 `P6` 的跨平台清理
- `Kimi` 更适合作为当前 `V1` 的唯一正式 provider
- `Claude Code` 的最佳接入面更偏 `CLI / SDK + hooks`，适合作为第二阶段扩展
- 即使本地已放入 Claude Code 源码，也只作为 `V2` 设计参考，不改变当前后续 `P7 -> P8 -> P9 -> P10 -> V2 Claude` 的阶段顺序

## Agent 分配建议

当前推荐规则：

- `P0-P3`：已完成
- `P4`：`单 agent 串行`
- `P4.5`：`单 agent 串行`
- `P5`：`谨慎双 agent 并行`
- `P6`：`单 agent 串行`
- `P7`：`单 agent 串行`
- `P8`：`单 agent 串行`
- `P9`：`单 agent 串行`
- `P10`：可按模块边界并行
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

当前进度口径：

- `P5-1` 已完成
- `P5-1.5` 已完成
- `P5-2` 已完成
- `P5-3` 已完成
- `P5` 已完成
- `P6-1` 已完成
- `P6-2` 已完成
- `P6-3` 已完成
- `P6` 已完成
- `P6.5` 已完成
- 当前进入 `P7 Local Session Interaction UI`

## Agent 任务模板

以下模板保留为 `P6` 收口阶段归档模板，用于后续回看拆分方式；不代表当前阶段回退，项目当前已进入 `P7 Local Session Interaction UI`。

推荐模板：

```text
当前阶段：P6 Cross-Platform Cleanup

当前目标：
在不破坏 `P5` 多 remote 基线的前提下，清理 Windows / PowerShell 假设与平台耦合，为后续 `P7` 与 `P8` 提供更稳定的跨平台底座。

当前前提：
- P5 已完成
- multi-remote server registry 已建立
- approval 已具备 `remote_id + request_id` 唯一定位规则
- desktop 已具备 multi-remote view 与最小 remote 状态标记
- recovery 当前仍以 contract 为准，不把未实现恢复系统写成既有能力

这次只做：
- 清理 Windows 路径硬编码
- 清理 PowerShell-only 假设
- 收敛路径、编码与换行策略
- 抽离平台相关入口或壳层逻辑，避免核心层依赖 Windows/macOS 专属 API
- 保持 `relay -> remote-agent -> provider` 主链路不回退
- 保持现有 multi-remote snapshot / approval / session 语义不回退

这次不要做：
- Codex
- Claude
- desktop 大重构
- 持久化实现
- recovery 系统实现扩张
- 回退去扩展旧 bridge
- 提前进入 `P7` 或 `P8`

允许修改：
- relay/
- desktop/
- remote-agent/
- README.md
- DEV.md
- 对应阶段 worklog

完成标准：
- 核心层不再依赖 Windows 专属能力
- 现有 multi-remote approval / session / snapshot 语义不回退
- README、DEV 与阶段 worklog 对当前 P6 目标表述一致
- 告诉我你修改了哪些文件
- 告诉我哪些平台耦合已被清理
```

## 当前常用命令

默认先切到仓库根目录。
如果使用虚拟环境，请先按当前 shell 的方式激活；这里不再写死 PowerShell 或 Windows 专用激活命令。

### 运行 relay

```text
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

### 运行 desktop

```text
cd desktop
npm install
npm start
```

首发公开 Beta 的 desktop 交付基线保持 source-run；当前没有额外
build / package / installer 步骤。
桌面端的最小交付说明见 `desktop/README.md`。

默认 `desktop` 读取 `http://127.0.0.1:8000`；如需覆盖，可设置
`RELAY_BASE_URL`。

### 运行 remote-agent

本地开发或调试 CLI：

```text
python -m pip install -e ./remote-agent
remote-agent serve
remote-agent kimi start --task "重构 auth 模块"
remote-agent sessions
```

首发公开 Beta 试用时，远端 env 至少还需要显式补充：

```text
REMOTE_AGENT_RELAY_ENDPOINT=http://<local-relay-host>:8000
REMOTE_AGENT_CONTROL_BASE_URL=http://<remote-host>:8711
REMOTE_AGENT_REMOTE_NAME=<unique-remote-id>
```

其中 `REMOTE_AGENT_CONTROL_BASE_URL` 必须是本地 `relay` 可回连的远端地址；
不应保留为默认的 `127.0.0.1`。

### 远端 Linux 部署 remote-agent

以下 deploy 命令只适用于远端 Linux host。
deploy 壳层继续留在 `remote-agent/deploy/` 与 `remote-agent/scripts/`，不进入共享 runtime 核心：

```text
cd remote-agent
bash scripts/install-systemd-user.sh --start
```

`P6-3` 当前固定边界：

- Linux deploy 壳层继续留在 `remote-agent/deploy/` 与 `remote-agent/scripts/`
- desktop 平台分支继续留在 `desktop/main.js`
- `relay/` 与 `remote-agent/src/remote_agent/` 不继续吸收 `systemctl`、`/bin/bash`、`loginctl`、Linux home 路径等 deploy 假设
- `desktop/preload.js`、renderer 与 state 不继续吸收 macOS / Windows 平台分支

非 PATH 安装的 `kimi` 应通过 `KIMI_BIN` 或 `--kimi-bin` 显式指定；共享 runtime 不再默认探测 Linux home 路径下的 provider 二进制。

### 当前远端部署策略

`P4` 默认采用：

- `systemctl --user`
- Linux deploy 壳层保留在 `remote-agent/deploy/` 与 `remote-agent/scripts/`

后续如需兼容更多环境，再补显式 deploy 或 provider 配置入口，但不恢复共享 runtime 内的 Linux-home fallback。

## 总结

`P0-P6.5` 已完成。当前阶段已切换到 `P7 Local Session Interaction UI`。后续顺序保持为 `P7 -> P8 -> P9 -> P10 -> V2 Claude`，不回退既有 `relay`、desktop MVP、hosted session CLI 与 multi-remote approval / session 一致性规则，也不把当前 recovery contract 误写成已实现恢复系统。
