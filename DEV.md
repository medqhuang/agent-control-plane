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

- 已完成：`P0`、`P1`、`P1.5`、`P2`、`P2.5`、`P3`、`P4`、`P4.5`、`P4.5-A`、`P4.5-B`、`P4.5-C`、`P4.5-D`、`P5`、`P5-1`、`P5-1.5`、`P5-2`、`P5-3`
- 当前阶段：`P6.5 Public Beta Release`
- 当前节点：`P6.5 Public Beta Release`
- 下一节点：`P7 Codex Support`
- 下一阶段：`P7 Codex Support`
- `V1` 暂不接入 `Claude Code`

当前主线已完成 `P5 Multi-Remote` 与 `P6 跨平台清理` 收口，当前进入 `P6.5 Public Beta Release`。
当前阶段也不以实时聊天 UI 或推理链可视化作为主目标；后续实时会话控制属于平台增强能力，不改变控制平面的产品定位。
`P6-1`、`P6-2` 与 `P6-3` 已完成；`P6` 整体已完成，阶段收口记录见 `P6_worklog.md`。

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
  与 `references/claude-code-haha-main/src/bridge/` 作为 `P6` 与 `P8` 的实现参考
- 当前不因为本地已有 Claude Code 源码而提前进入 `Claude Code Support`
- 当前不因为本地已有 Claude Code 源码而改变 `P6 -> P6.5 -> P7 -> P8 -> V2 Claude` 的阶段顺序
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
- `当前`：`P6` 跨平台清理
- `后续`：`P6.5` Public Beta Release
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

`P4.5` 已完成；其后续 `P5 Multi-Remote` 与 `P6 跨平台清理` 也已完成，当前进入 `P6.5 Public Beta Release`。

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

- 当前阶段
- 当前节点：`P6.5 Public Beta Release`

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
- 截图或演示材料

### 不包含

- `Codex Support`
- `Claude Code`
- `P8` 级别的可靠性硬化
- 商业级安装器
- 多设备切换

### 完成标准

- 新用户可以按照文档完成一次本地控制端启动
- 新用户可以完成一次远端 `remote-agent` 安装与启动
- 新用户可以启动一个 `Kimi` hosted session 并完成一次本地审批
- 仓库具备对外公开试用所需的最小说明、限制与反馈入口

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
- `Kimi` 与 `Codex` 更适合当前控制平面主线
- `Claude Code` 的最佳接入面更偏 `CLI / SDK + hooks`，适合作为第二阶段扩展
- 即使本地已放入 Claude Code 源码，也只作为 `V2` 设计参考，不改变当前 `P6 -> P6.5 -> P7 -> P8 -> V2 Claude` 的阶段顺序

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
- 当前进入 `P6.5`

## Agent 任务模板

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
python -m uvicorn relay.main:app --reload
```

### 运行 desktop

```text
cd desktop
npm start
```

### 运行 remote-agent

本地开发或调试 CLI：

```text
python -m pip install -e ./remote-agent
remote-agent serve
remote-agent kimi start --task "重构 auth 模块"
remote-agent sessions
```

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

后续如需兼容更多环境，再补 fallback。

## 总结

`P0-P6` 已完成。当前阶段已切换到 `P6.5 Public Beta Release`。后续顺序保持为 `P6.5 -> P7 -> P8 -> V2 Claude`，不回退既有 `relay`、desktop MVP、hosted session CLI 与 multi-remote approval / session 一致性规则，也不把当前 recovery contract 误写成已实现恢复系统。
