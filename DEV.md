# DEV

本文件用于维护者协作与当前阶段执行控制。

## 当前阶段

- 当前阶段：`P8 V1.0 Release`
- 当前子目标：`P8 V1 Scope Freeze And Release Surface Audit`
- 已完成：`P0-P7`、`P7-A`、`P7-B`、`P7-C`、`P7-D`
- 下一阶段：`P9 Codex Support`
- 当前唯一正式 provider：`Kimi`

当前阶段只做 `v1.0` 口径冻结、release surface 审计、最小试用路径统一与
已知限制收口，不前推到 `P9`、`P10` 或 `V2 Claude`。

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
Create a file named acp-v1-proof.txt in the current directory, but ask for approval before writing anything.
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

## P8 本轮 blocker 审计结论

### Release-blocking

- 本轮基于仓库静态审计，没有识别出一个已经被当前代码明确暴露、且必须立刻修实现才能让 `v1.0` 文档成立的 confirmed code blocker
- 本轮没有做真实远端完整链路复跑，因此也没有把“未复跑 live E2E”误写成“已确认无实现风险”

### Non-blocking but must be documented

- source-run / source-install 仍是当前正式交付面
- `relay` / `remote-agent` 内存态与重启不恢复
- 仅 `Kimi`
- 仅本地 Windows + 远端 Linux
- 手工 env / 网络检查
- `watch` 单次读取
- `attach` 缺失

### Doc-only issues fixed in this round

- README 仍保留 `P7` 之前的旧限制描述
- P6.5 文档的阶段推进写错到 `P7 Codex Support` / `P8 Reliability`
- 根文档对 `logs/` 下文件的引用路径不统一
- `desktop/README.md` 与 `remote-agent/README.md` 未对齐当前 `session detail + reply + approval` 闭环

## 后续顺序

- 当前仍停留在 `P8`
- 当前子目标完成后，下一步仍是 `P9 Codex Support`
- 不因为文档收口提前进入 `P10`

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
