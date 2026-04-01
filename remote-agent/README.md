# remote-agent

本文件定义当前 `v1.0` 的远端 `remote-agent` 安装面、托管面与最小运行路径。

配套文档：

- `README.md`
- `DEV.md`
- `logs/P8_worklog.md`
- `logs/P6.5_trial_guide.md`

## 当前定位

`remote-agent` 是当前正式架构中的远端托管执行面：

`desktop -> relay -> remote-agent -> provider native interface`

当前 `v1.0` 已实现的最小能力：

- `remote-agent serve`
- 远端 Linux `systemd --user` 长驻
- `remote-agent kimi start --task "..."` 启动 hosted session
- `remote-agent sessions / watch / reply / stop`
- 远端向 `relay` 上报 session / approval 标准事件
- 接收来自 `relay` 的 approval 决策并回写给 hosted `Kimi` session

## 当前正式承诺面

- 远端正式承诺平台：Linux
- 当前唯一正式 provider：`Kimi --wire`
- 当前正式长期运行方式：`systemd --user`
- 当前交付形态：repo 内 source-install

## 当前不承诺

- `Codex`
- `Claude`
- `attach`
- PyPI 包 / wheel / 系统发行包
- 非 Linux deploy 面
- restart recovery / checkpoint / replay
- provider 执行现场 `resume / reattach`

## 安装方式

本地开发或调试 CLI：

```bash
python -m pip install -e ./remote-agent
```

远端 Linux 安装与长驻：

```bash
cd ~/agent-control-plane/remote-agent
bash scripts/install-systemd-user.sh --start
```

## 常用命令

```bash
remote-agent serve
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
remote-agent sessions
remote-agent watch <session_id>
remote-agent reply <session_id> --message "..."
remote-agent stop <session_id>
```

`remote-agent attach <session_id>` 当前未实现。

## install script 已自动完成的内容

- 创建 venv：`~/.venvs/agent-control-plane`
- 从当前 workdir 执行 `python -m pip install -e`
- 写入基础 env：
  - `REMOTE_AGENT_HOST`
  - `REMOTE_AGENT_PORT`
  - `REMOTE_AGENT_LOG_LEVEL`
  - `REMOTE_AGENT_LOG_FILE`
- 渲染 `~/.config/systemd/user/remote-agent.service`
- 执行 `systemctl --user daemon-reload`
- 执行 `systemctl --user enable remote-agent.service`
- 在 `--start` 下启动服务
- 尝试确保 linger

## 仍需手工完成的内容

- 编辑 `~/.config/remote-agent/remote-agent.env`
- 补充 `REMOTE_AGENT_RELAY_ENDPOINT`
- 补充 `REMOTE_AGENT_CONTROL_BASE_URL`
- 建议补充 `REMOTE_AGENT_REMOTE_NAME`
- 确认远端到本地 `relay` 的连通性
- 确认本地 `relay` 到远端控制面的回连
- 确认 `kimi` 在 PATH 中，或显式提供 `KIMI_BIN`

最小必填 env：

```bash
REMOTE_AGENT_RELAY_ENDPOINT=http://<local-relay-host>:8000
REMOTE_AGENT_CONTROL_BASE_URL=http://<remote-host>:8711
REMOTE_AGENT_REMOTE_NAME=<unique-remote-id>
```

## `Kimi` 发现顺序

1. `remote-agent kimi start --kimi-bin ...`
2. `KIMI_BIN`
3. PATH 中的 `kimi`

当前没有共享 runtime 中的 Linux-home provider fallback。

## 最小验证命令

```bash
systemctl --user status remote-agent.service --no-pager
remote-agent sessions
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
tail -n 50 ~/.local/state/remote-agent/remote-agent.log
```

## 与本地 UI 配合的最小闭环

### 1. 本地先启动 `relay` 与 `desktop`

本地 Windows：

```powershell
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd desktop
npm install
npm start
```

### 2. 远端安装并启动服务

远端 Linux：

```bash
cd ~/agent-control-plane/remote-agent
bash scripts/install-systemd-user.sh --start
```

补 env 后重启：

```bash
systemctl --user restart remote-agent.service
systemctl --user status remote-agent.service --no-pager
```

### 3. 远端启动一个 hosted session

```bash
mkdir -p ~/acp-v1-trial
cd ~/acp-v1-trial
remote-agent kimi start --task "Inspect the current directory and wait for my next instruction."
```

### 4. 在本地 UI 中查看 session

当前应在本地 `desktop` 中看到该 session，并能打开 session detail。

### 5. 在本地 UI 中提交一轮 `reply`

推荐用本地 UI 发送：

```text
Create a file named acp-v1-proof.txt in the current directory, but ask for approval before writing anything.
```

### 6. 在本地 UI 中处理一轮 approval

如果该轮 reply 触发 approval，应在本地 UI 中处理 `Approve` / `Reject`，
然后观察 session 继续执行。

## Hosted Session Contract

- `remote-agent kimi start --task "..."` 创建后台托管 session
- 命令本身只等待首个 checkpoint，然后返回
- 返回后 session 由 `remote-agent serve` 托管，不再由启动它的 shell 持有
- `remote-agent sessions` 只列当前 runtime 中仍在托管的 session，不是持久化历史视图
- `remote-agent watch <session_id>` 是单次读取，不是持续 follow
- `remote-agent reply <session_id> --message "..."` 是非 `attach` 模式下追加一轮输入
- `remote-agent stop <session_id>` 只在 session 空闲时允许执行
- `remote-agent stop <session_id>` 当前拒绝：
  - `approval_pending`
  - turn 仍在运行中的 session

## Recovery Boundary

当前必须严格区分三层能力：

- 服务复活
- 控制面状态恢复
- provider 执行现场恢复

当前真实边界：

- 只要远端 `remote-agent serve` 与 provider 子进程仍存活，本地 `desktop` 关闭后 hosted session 仍继续运行
- 本地 `desktop` 重开后只能重新连接 `relay` 并读取 `relay` 仍保留在内存中的状态
- `relay` 重启后不会自动恢复旧 snapshot
- `remote-agent` 重启后不会自动恢复旧 hosted session / pending approvals / request 映射
- 当前不承诺 provider 原始执行现场 `resume / reattach`

## 当前已知限制

- source-install 仍是当前正式交付形态
- 手工 env 仍是当前正式路径的一部分
- 网络检查仍需手工完成
- `watch` 不是持续 follow
- `attach` 未实现
- `relay` 与 `remote-agent` 都仍是内存态
