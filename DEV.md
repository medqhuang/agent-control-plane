# DEV

这份文档只服务一件事：指导你把项目按阶段拆开，并把每一阶段清楚地分配给 agent。

## 项目一句话

这是一个面向远程 AI 编码 CLI 的控制平面。

核心链路只有一条：

```text
本地控制应用
    ↓
SSH 隧道 / 本地网络
    ↓
远程 Relay
    ↓
Provider Adapter
    ↓
Kimi / Claude / Codex CLI
```

项目目标：
- 统一监控多个 remote 上的多个 agent session
- 统一接收 approval request
- 统一在本地 approve / reject

平台边界：
- 本地开发：Windows
- 本地目标：Windows + macOS
- 远程 provider：Linux

硬约束：
- relay 是状态真源
- approval 必须用 `request_id`
- 所有 session 事件必须带 `seq`
- 超时只能 `reject` 或 `expire`
- 核心层不能写死 Windows 路径、PowerShell、Windows / macOS 平台 API

## 阶段总览

- `已完成`：`P0` 项目初始化
- `已完成`：`P1` Relay Core
- `已完成`：`P1.5` Relay 收口
- `已完成`：`P2` Kimi 闭环
- `已完成`：`P2.5` Kimi bridge 收口
- `当前`：`P3` 本地控制端 MVP
- `后续`：`P4` Multi-Remote
- `后续`：`P5` 跨平台清理
- `后续`：`P6` Claude Support
- `后续`：`P7` Codex Experimental
- `后续`：`P8` 可靠性增强

## 当前基线

进入 `P3` 前，relay 与 Kimi bridge 已具备下面这些稳定基线：

- `GET /v1/snapshot`
- `POST /v1/approval-response`
- in-memory `session store`
- in-memory `approval store`
- 最小 `event log`
- approval 幂等保护
- approval / session 状态一致性
- Kimi 最小真实远端 approval 闭环
- remote-backed 失败 / 超时不污染本地状态

进入 `P3` 时默认冻结以下规则，不要顺手重构：

- `approved -> session=running`
- 相同决策重复提交：返回成功，但不重复写事件
- 冲突决策重复提交：返回 `409`
- relay 仍然是状态真源
- 先 remote writeback 成功，再提交本地状态

当前 bridge 限制也一并冻结认知：

- `request_id` 仍是 adapter 派生，不是 Kimi 原生 ID
- writeback 仍依赖 `tmux` 与当前 TUI 布局
- relay 仍为 in-memory 状态
- 当前能力足以进入 `P3`，但不足以宣称为生产级集成

## P0 项目初始化

目标：
- 让仓库进入可编码状态

agent 分配建议：
- `单 agent 串行`
- 原因：项目还在定基础结构，不适合并行扩散

这一阶段 agent 做什么：
- 初始化 Git 仓库
- 创建 `relay/`、`adapters/`、`desktop/` 基础目录
- 建立 Python 开发环境
- 选定 relay 技术栈

这一阶段不要做：
- provider adapter
- UI
- 远程联调

完成标准：
- 本地能开始写 relay 代码

## P1 Relay Core

目标：
- 先把控制平面核心立住

agent 分配建议：
- `单 agent 串行`
- 原因：接口、数据结构、目录边界都还在收敛

这一阶段 agent 做什么：
- 在 `relay/` 下实现最小 HTTP 服务
- 实现 in-memory `session store`
- 实现 in-memory `approval store`
- 实现最小 `event log`
- 实现 `GET /v1/snapshot`
- 实现 `POST /v1/approval-response`
- 用假数据返回 1 个 session 和 1 个 approval

这一阶段不要做：
- provider adapter
- 本地 UI
- 多 remote
- 持久化

完成标准：
- 本地启动 relay
- 访问 `GET /v1/snapshot` 能返回固定 JSON

当前状态：
- `已完成`

## P1.5 Relay 收口

目标：
- 在进入真实 provider 前，先把 relay 状态语义收稳

agent 分配建议：
- `单 agent 串行`
- 原因：这是 P1 和 P2 之间的收口阶段，必须统一规则

这一阶段 agent 做什么：
- 统一 approval 和 session 的最小状态关系
- 给 `approval-response` 增加幂等保护
- 阻止冲突决策污染事件流

完成标准：
- snapshot 中 approval 与 session 状态不矛盾
- 相同决策重复提交不重复写事件
- 冲突决策重复提交返回 `409`

当前状态：
- `已完成`

## P2 Kimi 闭环

目标：
- 跑通第一条真实 provider 链路

agent 分配建议：
- `单 agent 串行`
- 原因：provider 接入和 relay 仍然强耦合，过早并行容易串改

这一阶段 agent 做什么：
- 在 `adapters/kimi/` 下实现 Kimi adapter
- 把 Kimi 原生事件映射成标准事件
- 把 approval request 写入 relay
- 把 approval response 回写到远程 session
- 完成一次真实 approval 闭环

这一阶段不要做：
- Claude
- Codex
- 桌面端美化
- 回退 P1.5 已冻结的状态规则

完成标准：
- 远程 Kimi 触发审批
- 本地能看到审批
- 本地点批准后远程继续执行

当前状态：
- `已完成`

## P2.5 Kimi Bridge 收口

目标：
- 在进入本地控制端前，先把 Kimi bridge 的远端链路语义收稳

agent 分配建议：
- `单 agent 串行`
- 原因：这是 bridge contract 固化阶段，必须统一口径

这一阶段 agent 做什么：
- 固化当前 Kimi bridge contract
- 保证先 remote writeback 成功，再提交本地状态
- 复核远端 `approve` 路径
- 复核远端 `reject` 路径
- 复核 remote-backed failure / timeout 路径

这一阶段不要做：
- 本地 UI
- 多 remote
- relay 重构
- 把 bridge 包装成官方协议级集成

完成标准：
- 真实远端 `approve` 路径通过
- 真实远端 `reject` 路径通过
- remote-backed failure / timeout 不污染本地状态
- 当前 bridge 限制被明确记录

当前状态：
- `已完成`

## P3 本地控制端 MVP

目标：
- 做出第一个能操作的本地界面

agent 分配建议：
- `可双 agent 并行`
- 前提：relay 接口已稳定
- 适合拆分：
  - 一个 agent 做 session 列表
  - 一个 agent 做 approvals 列表和 approve / reject

这一阶段 agent 做什么：
- 实现 session 列表
- 实现 pending approvals 列表
- 实现 approve / reject 操作
- 展示 server 连接状态

这一阶段不要做：
- 托盘动画
- 灵动岛
- 桌宠

完成标准：
- 不看 SSH 终端，也能完成一次完整审批

当前状态：
- `当前阶段`

## P4 Multi-Remote

目标：
- 从单机原型升级成多服务器控制台

agent 分配建议：
- `可双 agent 并行`
- 前提：本地控制端已有稳定单 remote 版本
- 适合拆分：
  - 一个 agent 做 server registry / snapshot 聚合
  - 一个 agent 做本地状态展示与 disconnected 标记

这一阶段 agent 做什么：
- 实现 server registry
- 支持多个 relay endpoint
- 聚合多个 snapshot
- 标记 disconnected 状态

这一阶段不要做：
- 新 provider
- 高级权限系统

完成标准：
- 两台远程服务器可同时显示在一个本地界面中

## P5 跨平台清理

目标：
- 把核心层整理成真正可迁移到 macOS 的结构

agent 分配建议：
- `单 agent 串行`
- 原因：这是收口阶段，最好统一整理，不适合多人同时改核心

这一阶段 agent 做什么：
- 清理硬编码 Windows 路径
- 清理 PowerShell 假设
- 抽离平台通知、托盘、菜单栏相关逻辑
- 明确编码、换行、路径处理策略

这一阶段不要做：
- 新功能扩张
- 新 UI 花样

完成标准：
- 核心层不依赖 Windows 专属能力
- 本地控制端迁移到 macOS 不需要推倒重来

## P6 Claude Support

目标：
- 接入第二个正式 provider

agent 分配建议：
- `可双 agent 并行`
- 前提：Kimi 链路已稳定
- 适合拆分：
  - 一个 agent 做 Claude adapter
  - 一个 agent 做本地控制端兼容 Claude 的展示层调整

这一阶段 agent 做什么：
- 实现 Claude adapter
- 完成 Claude 事件标准化
- 跑通 Claude approval 闭环

完成标准：
- Kimi 和 Claude 能同时被本地控制端监控

## P7 Codex Experimental

目标：
- 接入实验性第三 provider

agent 分配建议：
- `单 agent 串行`
- 原因：实验适配不确定性高，最好由一个 agent 连续收敛

这一阶段 agent 做什么：
- 实现 Codex wrapper adapter
- 暴露基础生命周期
- 拦截 approval 提示

这一阶段不要做：
- 细粒度 step 语义承诺

完成标准：
- 本地能看到 Codex session 生命周期和 approval 卡点

## P8 可靠性增强

目标：
- 让系统具备日常使用可信度

agent 分配建议：
- `可多 agent 并行`
- 前提：核心功能已基本稳定
- 适合拆分：
  - 一个 agent 做 reconnect / timeout
  - 一个 agent 做 approval 幂等和 stale request 保护
  - 一个 agent 做日志和观测性增强

这一阶段 agent 做什么：
- reconnect
- heartbeat timeout
- approval 幂等
- stale request 保护
- 更清晰的日志

完成标准：
- 断线后状态不乱
- 重复审批不会有副作用
- 超时不会错误放行

## 给 agent 的分配规则

每次只分配一个小切片，最多覆盖一个阶段里的一个点。

总规则：
- `P0-P2.5`：单 agent 串行
- `P1.5`：单 agent 收口
- `P3-P4`：谨慎双 agent 并行
- `P5`：单 agent 收口
- `P6`：可双 agent 并行
- `P7`：单 agent 实验收敛
- `P8`：按模块边界并行

好的分配方式：
- “只做 `GET /v1/snapshot`”
- “只做 in-memory session store”
- “只做 Kimi approval request 入 relay”

不要这样分配：
- “把 P1 全做完”
- “把 relay、Kimi、本地 UI 一次打通”

每次给 agent 的任务都要包含：
- 当前阶段
- 当前唯一目标
- 这次只做什么
- 这次不要做什么
- 允许修改哪些目录
- 完成标准

推荐模板：

```text
当前阶段：P3 本地控制端 MVP

当前目标：
实现本地 session 列表和 pending approvals 列表。

这次只做：
- 本地 session 列表
- 本地 pending approvals 列表
- 本地 approve / reject 操作入口

这次不要做：
- 多 remote
- Claude
- Codex
- 重构 relay
- 重构 Kimi bridge

允许修改：
- desktop/

完成标准：
- 本地界面能显示 session 和 pending approvals
- 告诉我验证步骤
```

## 命令建议

以下命令以 Windows 本地开发为主。

### 初始化仓库

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane
git init
git status
```

### 创建 Python 环境

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 如果采用 FastAPI 做 relay

```powershell
pip install fastapi uvicorn pydantic
```

### 运行 relay

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane
.venv\Scripts\Activate.ps1
python -m uvicorn relay.main:app --reload
```

### 测试 snapshot 接口

```powershell
Invoke-WebRequest http://127.0.0.1:8000/v1/snapshot
```

### 查看项目文件

```powershell
Get-ChildItem -Recurse
```

### 记录当前改动

```powershell
git status --short
git diff
```

一句话收尾：

`P0-P2.5` 已完成，当前只推进 `P3 本地控制端 MVP`，不要顺手回退 bridge 规则。
