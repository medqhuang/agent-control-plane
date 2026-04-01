# Agent Control Plane

面向远程 AI 编码 CLI 的自托管控制平面。

当前正式主链路固定为：

`desktop -> relay -> remote-agent -> provider native interface`

## 当前阶段

- 当前阶段：`P9 Codex Support`
- 当前子目标：`P9 Codex Support`
- 已完成：`P0-P7`、`P7-A`、`P7-B`、`P7-C`、`P7-D`
- 已完成发布闸门：`P8 V1.0 Release`
- 下一阶段：`P10 Reliability Reinforcement`
- 当前唯一正式 provider：`Kimi`

`P8 v1.0` 的 live end-to-end trial verification 已完成，当前仓库已前推到
`P9 Codex Support`。`v1.0` 的对外口径继续只覆盖已经真实验证通过的 `Kimi`
主链路，不把 `P10` 或 `V2 Claude` 的内容提前写成当前已支持。

## v1.0 已承诺能力

- 本地 Windows source-run `desktop`
- 本地 operator-run `relay`
- 远端 Linux `remote-agent` + `systemd --user`
- 多 remote 聚合
- approval 继续按 `remote_id + request_id` 唯一定位
- 本地 session 列表
- 本地 session 详情与最近回复查看
- 本地对 hosted session 提交一轮 `reply`
- 本地统一 `approve / reject`
- 远端 `remote-agent sessions / watch / reply / stop`
- `Kimi --wire` hosted session 主链路

## v1.0 未承诺能力

- `P9 Codex Support`
- `P10` reconnect / checkpoint / replay / pending approvals replay
- `P10` `remote-agent` 重启恢复与 provider 执行现场恢复
- `V2 Claude`
- `attach`
- 通用聊天工作台
- token 流透传
- 推理链可视化
- installer
- 云 relay / 云服务
- 多设备 / 账号体系

## 最小安装与试用路径

当前 `v1.0` 的最小试用路径以“本地 Windows 控制端 + 远端 Linux 托管端”为准。
它验证的是已经实现的最小闭环：本地启动、远端托管、UI 里看到 session、从 UI
发一轮 `reply`、再处理一轮 approval。

### 1. 本地启动 `relay`

在仓库根目录执行：

```powershell
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

可选自检：

```powershell
curl.exe http://127.0.0.1:8000/v1/snapshot
```

### 2. 本地启动 `desktop`

打开第二个本地 shell：

```powershell
cd desktop
npm install
npm start
```

当前 `desktop` 默认连接 `http://127.0.0.1:8000`。如需覆盖，显式设置
`RELAY_BASE_URL`。

### 3. 远端安装并启动 `remote-agent`

把 `remote-agent/` 放到远端 Linux 主机后执行：

```bash
cd ~/agent-control-plane/remote-agent
bash scripts/install-systemd-user.sh --start
```

当前 install script 会自动完成：

- 创建 venv
- `python -m pip install -e <workdir>`
- 写入基础 `REMOTE_AGENT_HOST` / `REMOTE_AGENT_PORT` / 日志 env
- 渲染并启用 `systemd --user` service

当前仍需手工补充远端 env：

```bash
REMOTE_AGENT_RELAY_ENDPOINT=http://<local-relay-host>:8000
REMOTE_AGENT_CONTROL_BASE_URL=http://<remote-host>:8711
REMOTE_AGENT_REMOTE_NAME=<unique-remote-id>
```

然后重启服务：

```bash
systemctl --user restart remote-agent.service
systemctl --user status remote-agent.service --no-pager
```

### 4. 远端确认网络与 `Kimi`

远端确认能访问本地 `relay`：

```bash
curl http://<local-relay-host>:8000/v1/snapshot
```

本地确认能访问远端控制面：

```powershell
curl.exe http://<remote-host>:8711/healthz
```

远端确认 `Kimi` 可用：

```bash
which kimi
kimi info
```

如果 `kimi` 不在 PATH 中，使用 `KIMI_BIN` 或 `--kimi-bin`。

### 5. 远端启动一个 hosted session

建议先启动一个会出现在 UI 中、但不强依赖首轮就触发 approval 的任务：

```bash
mkdir -p ~/acp-v1-trial
cd ~/acp-v1-trial
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
```

当前 live 验证已确认：在 service mode 下，当不显式传 `--workdir` 时，
`remote-agent kimi start` 会默认继承 CLI 调用目录。

如果 `kimi` 不在 PATH：

```bash
remote-agent kimi start --kimi-bin /path/to/kimi --task "Inspect the current directory and wait for my next instruction."
```

当前 contract 下，`remote-agent kimi start --task "..."` 只等待首个 checkpoint
后返回；返回后 session 继续由 `remote-agent serve` 托管。

### 6. 在本地 UI 中查看 session

保持本地 `desktop` 打开，确认：

- session 列表里出现新的 hosted session
- 选中 session 后能打开 session detail
- detail 中能看到最近 turn / transcript / reply composer

### 7. 在本地 UI 中提交一轮 `reply`

在 session detail 的 reply 输入框中提交一条更可能触发 approval 的指令：

```text
Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.
```

当前 live 验证中，这条显式 shell-tool 文案已真实触发一轮 approval，并在本地 UI
中完成 `Approve -> session continue -> detail 回流`。

这一步验证的是当前 `v1.0` 已实现的“本地 UI -> relay -> remote-agent -> hosted session”
reply 主链路。

### 8. 在本地 UI 中处理一轮 approval

如果该轮 reply 触发 approval，当前 UI 应同时支持两种入口：

- approvals 列表中的 `Approve` / `Reject`
- session detail 中的 approval context 与 `Approve` / `Reject`

完成一轮决策后，应看到该 hosted session 继续执行，且 session detail 刷新到
最新结果。

## 已知限制

- 当前正式 provider 只有 `Kimi`
- 本地正式承诺平台是 Windows；远端正式承诺平台是 Linux
- `desktop` 仍是 source-run，不是 installer
- `relay` 仍需手工启动
- `remote-agent` 仍需手工补充 relay / control / remote-name env
- 本地到远端、远端到本地的网络连通性仍需手工确认
- `desktop` 当前以手工 refresh 为主，不承诺自动持续刷新
- `watch` 当前是单次读取，不是持续 follow
- `attach` 当前未实现
- `stop` 当前不能在 `approval_pending` 或 turn 运行中执行
- `relay` 与 `remote-agent` 仍是内存态；重启后不会恢复既有 session / approvals
- 当前不承诺 checkpoint、replay、pending approvals replay 或 provider `resume / reattach`

## 文档关系

- [logs/P8_worklog.md](logs/P8_worklog.md)
  - 当前 `P8` 收口记录与 blocker 审计结果
- [logs/P6.5_trial_guide.md](logs/P6.5_trial_guide.md)
  - 历史文件名保留；当前作为 `v1.0` operator-led 最小试用讲解文档继续使用
- [logs/P6.5_release_notes.md](logs/P6.5_release_notes.md)
  - 历史文件名保留；当前内容已同步为 `v1.0` release surface 说明
- [logs/P6.5_launch_checklist.md](logs/P6.5_launch_checklist.md)
  - 历史文件名保留；当前内容已同步为 `v1.0` release surface checklist
- [desktop/README.md](desktop/README.md)
  - 本地 Windows `desktop` 运行面
- [remote-agent/README.md](remote-agent/README.md)
  - 远端 Linux `remote-agent` 安装与托管面

`P6.5` 作为阶段已经结束；当前不再把这些文档当作“仍停留在 Beta 阶段”的口径。
它们现在只是沿用历史文件名的支撑文档，实际口径以当前 `P8` 同步后的内容为准。

## 路线图

- 已完成：`P0 -> P7`
- 已完成：`P8 V1.0 Release`
- 当前：`P9 Codex Support`
- 后续：`P10 Reliability Reinforcement`
- 更后续：`V2 Claude`

`P8` 已经通过 live release gate，当前文档状态已同步前推到 `P9 Codex Support`。
