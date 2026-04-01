# Agent Control Plane

面向远程 AI 编码 CLI 的自托管控制平面。

当前正式主链路固定为：

`desktop -> relay -> remote-agent -> provider native interface`

## Status

- 正式发布面：`v1.0`
- 当前仓库阶段：`P9 Codex Support`
- 已通过的发布闸门：`P8 V1.0 Release`
- 当前唯一已真实验证通过的 provider：`Kimi`

`v1.0` 的 live end-to-end trial verification 已完成。当前仓库已经进入
`P9 Codex Support`，但对外 `v1.0` 口径仍然只覆盖已经真实验证通过的
`Kimi` 主链路，不提前宣称 `Codex`、`P10` 可靠性增强或 `V2 Claude` 能力。

## What This Project Is

`Agent Control Plane` 用来把分散在远端服务器、不同 CLI、不同终端里的
session 状态、approval request 和后续交互，统一回收到本地控制端查看和处理。

它解决的不是“通用聊天 UI”问题，而是远程 AI 编码工作流中的控制面问题：

- 多个 remote 上同时存在多个 hosted session
- approval request 分散在远端 shell 中
- 本地缺少统一的 session / approval 视图
- 已托管 session 需要在本地继续 `reply`、`approve / reject`

## v1.0 Includes

当前 `v1.0` 已承诺并已收口的能力：

- 本地 Windows source-run `desktop`
- 本地 operator-run `relay`
- 远端 Linux `remote-agent` + `systemd --user`
- `Kimi --wire` hosted session 主链路
- multi-remote 聚合
- approval 按 `remote_id + request_id` 唯一定位
- 本地 session 列表
- 本地 session detail / recent transcript / recent reply
- 本地 UI 对 hosted session 提交 `reply`
- 本地 UI 统一 `approve / reject`
- 远端 `remote-agent sessions / watch / reply / stop`

## v1.0 Does Not Include

当前不能写成 `v1.0` 已支持的内容：

- `P9 Codex Support`
- `P10` reconnect / checkpoint / replay / pending approvals replay
- `P10` `remote-agent` 重启恢复
- provider 原始执行现场 `resume / reattach`
- `V2 Claude`
- `attach`
- 通用聊天工作台
- token 流透传
- 推理链可视化
- installer
- 云 relay / 云服务
- 多设备 / 账号体系

## Release Shape

当前正式发布形态不是 installer，而是 self-hosted 的源码发布面：

- `desktop`：本地 Windows source-run
- `relay`：本地 operator-run FastAPI 进程
- `remote-agent`：远端 Linux source-install + `systemd --user`

这意味着 GitHub Release 当前更接近：

- 仓库源码
- 配套 README / operator guide / release notes / checklist
- 远端安装脚本

而不是：

- `exe` / `msi`
- 自动更新桌面应用
- 托管云控制台

## Quick Start

当前最小试用路径固定为“本地 Windows 控制端 + 远端 Linux 托管端”。

### 1. Start Local `relay`

在仓库根目录执行：

```powershell
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

可选自检：

```powershell
curl.exe http://127.0.0.1:8000/v1/snapshot
```

### 2. Start Local `desktop`

打开第二个本地 shell：

```powershell
cd desktop
npm install
npm start
```

默认连接：`http://127.0.0.1:8000`

如需覆盖，显式设置 `RELAY_BASE_URL`。

### 3. Install And Start Remote `remote-agent`

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

仍需手工补充远端 env：

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

### 4. Verify Network And `Kimi`

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

### 5. Start A Hosted Session

```bash
mkdir -p ~/acp-v1-trial
cd ~/acp-v1-trial
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
```

当前 live 验证已确认：在 service mode 下，当不显式传 `--workdir` 时，
`remote-agent kimi start` 会默认继承 CLI 调用目录。

### 6. Open Session Detail In Local UI

保持本地 `desktop` 打开，确认：

- session 列表里出现新的 hosted session
- 选中后能打开 session detail
- detail 中能看到 recent turn / transcript / reply composer

### 7. Submit One `reply`

当前 live 验证中，下面这条文案可以稳定触发一轮 approval：

```text
Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.
```

### 8. Handle One `approval`

当前 UI 应支持两种入口：

- approvals 列表中的 `Approve` / `Reject`
- session detail 中 approval context 的 `Approve` / `Reject`

完成一轮决策后，应看到该 hosted session 继续执行，且结果回流到当前
session detail。

## Verified v1.0 Gate

`P8 V1.0 Release` 的 live gate 已通过。真实验证通过的链路包括：

- 本地 relay 可被远端访问
- 远端控制面可被本地回控
- 远端 `remote-agent` 安装、启动与 `Kimi` hosted session 启动
- 本地 UI session visible / detail 打开
- 本地 UI `reply` 提交
- 本地 UI `approval` 提交
- `approval` 后 session 继续执行并回流到 detail

发布闸门中识别并修复过一个 confirmed blocker：

- `remote-agent kimi start` 在 service mode 下，当省略 `--workdir` 时未正确继承
  CLI 当前目录
- 当前仓库中的 [remote-agent/src/remote_agent/cli.py](remote-agent/src/remote_agent/cli.py)
  已修复为默认发送 `os.getcwd()`

## Known Limitations

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

## Repository Layout

- [desktop](desktop)
  - 本地 Windows 控制端
- [relay](relay)
  - 本地控制面聚合层
- [remote-agent](remote-agent)
  - 远端 Linux 托管执行层
- [DEV.md](DEV.md)
  - 内部维护 / 阶段控制文档
- [logs/P9_worklog.md](logs/P9_worklog.md)
  - 当前 `P9 Codex Support` 拆分、验收与状态前推记录
- [logs/P8_worklog.md](logs/P8_worklog.md)
  - 已完成 `P8 V1.0 Release` 的 live gate、blocker 审计与收口记录

## Additional Docs

- [desktop/README.md](desktop/README.md)
  - 本地 Windows `desktop` 运行面
- [remote-agent/README.md](remote-agent/README.md)
  - 远端 Linux `remote-agent` 安装与托管面
- [logs/P6.5_trial_guide.md](logs/P6.5_trial_guide.md)
  - 历史文件名保留；当前作为 `v1.0` operator-led 最小试用讲解文档继续使用
- [logs/P6.5_release_notes.md](logs/P6.5_release_notes.md)
  - 历史文件名保留；当前内容已同步为 `v1.0` release surface 说明
- [logs/P6.5_launch_checklist.md](logs/P6.5_launch_checklist.md)
  - 历史文件名保留；当前内容已同步为 `v1.0` release surface checklist

`P6.5` 作为阶段已经结束；这些文件现在只是沿用历史文件名的支撑文档，
实际对外口径以 `v1.0` 和当前 README / DEV 同步后的内容为准。

## Roadmap

- 已完成：`P0 -> P7`
- 已完成：`P8 V1.0 Release`
- 当前：`P9 Codex Support`
- 后续：`P10 Reliability Reinforcement`
- 更后续：`V2 Claude`
