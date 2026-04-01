# DEV

本文件用于维护者协作与当前阶段执行控制。

## 当前阶段

- 当前阶段：`P9 Codex Support`
- 当前子目标：`P9 Codex Support`
- 已完成：`P0-P7`、`P7-A`、`P7-B`、`P7-C`、`P7-D`
- 已完成发布闸门：`P8 V1.0 Release`
- 下一阶段：`P10 Reliability Reinforcement`
- 当前唯一正式 provider：`Kimi`

`P8 v1.0` 的 live release gate 已通过，当前维护焦点已前推到 `P9 Codex Support`。
`v1.0` 文档继续只覆盖已经真实验证通过的 `Kimi` 主链路，不前写 `P10` 或
`V2 Claude` 能力。

## 固定架构与全局约束

- 顶层架构不改：`desktop -> relay -> remote-agent -> provider native interface`
- `relay` 负责本地控制面聚合，不代理 provider 原始模型数据流
- `remote-agent` 是远端 hosted session 的真实运行宿主
- approval 在 multi-remote 下必须以 `remote_id + request_id` 唯一定位
- 本地 `desktop` 不是远端 session 的生存依赖
- 恢复语义必须明确区分：
  - 服务复活
  - 控制面状态恢复
  - provider 执行现场恢复
- 文档与实现都不能把 contract-only 内容写成已交付能力

## v1.0 已承诺能力

- 本地 Windows source-run `desktop`
- 本地 operator-run `relay`
- 远端 Linux `remote-agent` + `systemd --user`
- `Kimi --wire` hosted session 主链路
- multi-remote 聚合
- approval 按 `remote_id + request_id` 唯一定位
- 本地 session 列表
- 本地 session 详情与最近回复查看
- 本地对 hosted session 提交 `reply`
- 本地统一 `approve / reject`
- 远端 `remote-agent sessions / watch / reply / stop`

## v1.0 未承诺能力

- `P9 Codex Support`
- `P10` reconnect / checkpoint / replay / pending approvals replay
- `P10` `remote-agent` 重启恢复
- `P10` provider 执行现场恢复
- `V2 Claude`
- `attach`
- 通用聊天工作台
- token 流透传
- 推理链可视化
- installer / 云 relay / 多设备 / 账号体系

## 最小发布与试用途径

当前对外最小路径固定为：

1. 本地启动 `relay`
2. 本地启动 `desktop`
3. 远端安装并启动 `remote-agent`
4. 远端启动一个 `Kimi` hosted session
5. 在本地 UI 中看到 session 并打开 detail
6. 在本地 UI 中提交一轮 `reply`
7. 在本地 UI 中处理一轮 approval

推荐用来验证 `reply -> approval` 闭环的 UI reply 文案：

```text
Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.
```

## 当前实现基线

仓库静态审计确认当前最小实现面包括：

- `relay/main.py`
  - `GET /v1/snapshot`
  - `GET /v1/sessions/{session_id}/detail`
  - `POST /v1/sessions/{session_id}/reply`
  - `POST /v1/approval-response`
- `remote-agent/src/remote_agent/app.py`
  - `GET /healthz`
  - `POST /v1/kimi/start`
  - `GET /v1/sessions`
  - `GET /v1/sessions/{session_id}`
  - `POST /v1/sessions/{session_id}/reply`
  - `POST /v1/sessions/{session_id}/stop`
- `desktop/src/renderer/features/sessions/render-session-detail.js`
  - session detail
  - recent transcript / recent reply
  - reply composer
  - approval context
- `desktop/src/renderer/state/snapshot-store.js`
  - session detail refresh
  - reply submission
  - approval continuation from UI context

## P6.5 文档与 P8 的关系

- `logs/P6.5_trial_guide.md`
  - 保留历史文件名
  - 当前继续作为 `v1.0` operator-led 试用讲解文档使用
- `logs/P6.5_release_notes.md`
  - 保留历史文件名
  - 当前内容同步为 `v1.0` release surface 说明
- `logs/P6.5_launch_checklist.md`
  - 保留历史文件名
  - 当前内容同步为 `v1.0` release surface checklist

结论：

- `P6.5` 作为阶段已经结束
- 历史文件名保留仅用于延续文档入口，不代表项目仍停留在 Beta 阶段
- 当前对外口径必须以 `P8` 同步后的内容为准

## 当前已知限制

- 当前唯一正式 provider 是 `Kimi`
- 本地正式承诺平台是 Windows；远端正式承诺平台是 Linux
- `desktop` 仍为 source-run
- `relay` 仍需手工启动
- `remote-agent` 仍需手工补 env
- 本地与远端网络检查仍是手工步骤
- `watch` 当前不是持续 follow
- `attach` 未实现
- `stop` 不能在 `approval_pending` 或 turn 运行中执行
- `relay` 与 `remote-agent` 都仍是内存态
- 当前不承诺 checkpoint、replay、pending approvals replay 或 provider `resume / reattach`

## P8 收口结论

### Live Verification Passed

- 已真实验证：本地 relay、desktop、远端 Linux `remote-agent`、真实 `Kimi` hosted session
- 已真实验证：本地 UI 可见 session、可打开 detail、可提交一轮 `reply`
- 已真实验证：本地 UI 可见 approval、可提交 `Approve`、决策后 session 继续执行并回流到 detail

### Confirmed Blocker Fixed

- `remote-agent kimi start` 在 service mode 下默认忽略 CLI 调用目录，已在
  `remote-agent/src/remote_agent/cli.py` 修复为默认继承 `os.getcwd()`
- 修复后已复跑验证：`cd <trial-dir> && remote-agent kimi start --task "..."` 会把
  hosted session workdir 落到调用目录

### Remaining Known Limitations

- source-run / source-install 仍是当前正式交付面
- `relay` / `remote-agent` 内存态与重启不恢复
- 仅 `Kimi`
- 仅本地 Windows + 远端 Linux
- 手工 env / 网络检查
- `desktop` 当前以手工 refresh 为主
- `watch` 单次读取
- `attach` 缺失

## 后续顺序

- `P8` 已通过 live release gate
- 当前阶段已前推到 `P9 Codex Support`
- 后续阶段仍按 `P10 Reliability Reinforcement -> V2 Claude` 推进

## 常用命令

### relay

```text
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

### desktop

```text
cd desktop
npm install
npm start
```

### remote-agent

```text
python -m pip install -e ./remote-agent
remote-agent serve
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
remote-agent sessions
```

### 远端 Linux 部署

```text
cd remote-agent
bash scripts/install-systemd-user.sh --start
```

仍需手工补充：

```text
REMOTE_AGENT_RELAY_ENDPOINT=http://<local-relay-host>:8000
REMOTE_AGENT_CONTROL_BASE_URL=http://<remote-host>:8711
REMOTE_AGENT_REMOTE_NAME=<unique-remote-id>
```
