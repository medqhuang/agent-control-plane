# desktop

本文件定义当前 `v1.0` 的本地 `desktop` 运行面。

配套文档：

- `README.md`
- `DEV.md`
- `logs/P8_worklog.md`
- `logs/P6.5_trial_guide.md`

## 当前定位

`desktop/` 是当前 `v1.0` 的本地 Windows 控制端壳层，负责：

- 查看 relay snapshot
- 查看 session 列表
- 打开 session detail
- 查看最近 transcript / recent reply
- 从本地 UI 提交一轮 `reply`
- 从本地 UI 提交 `Approve` / `Reject`

`desktop` 不负责：

- 自动启动 `relay`
- 自动安装远端 `remote-agent`
- 自动补写远端 env
- installer / package / auto-update

## 当前交付形态

- 交付形态：repo 内 source-run 目录
- 当前正式承诺平台：Windows
- 启动命令：`cd desktop`、`npm install`、`npm start`
- 当前脚本面：`package.json` 只提供 `start` 与 `dev`

## 最小依赖

- Node.js 与 npm
- 仓库副本
- 一个已启动且可访问的本地 `relay`

## relay 连接规则

- 默认连接：`http://127.0.0.1:8000`
- 如需覆盖：显式设置 `RELAY_BASE_URL`
- `desktop` 只消费 `relay` 提供的 snapshot / session detail / approval / reply API

## 最小启动路径

### 1. 本地启动 `relay`

```powershell
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

### 2. 本地启动 `desktop`

```powershell
cd desktop
npm install
npm start
```

### 3. 等待远端 session 出现

当远端 `remote-agent` 启动 hosted session 并把事件上报给 `relay` 后，
本地 `desktop` 应能看到：

- session 列表中的新 session
- 选中后可打开 session detail
- detail 中的 recent transcript / reply composer

### 4. 从本地 UI 提交一轮 `reply`

当前最小验证方式是在 session detail 的 reply 输入框中提交一条更容易触发 approval
的文案，例如：

```text
Create a file named acp-v1-proof.txt in the current directory, but ask for approval before writing anything.
```

### 5. 在本地 UI 中处理一轮 approval

当前 UI 支持：

- approvals 列表中的 `Approve` / `Reject`
- session detail 中 approval context 的 `Approve` / `Reject`

## 当前可见结果

- session list 显示 `relay` 当前 snapshot 中的 hosted sessions
- session detail 显示 hosted session metadata、recent turn 与 recent transcript
- reply composer 可把新一轮输入经 `relay` 转发到目标 hosted session
- pending approvals 列表显示待处理 approval 请求
- approval 决策会先提交给 `relay`，再由 `relay` 回写到对应远端 `remote-agent`

## 当前边界

- `desktop` 仍是 source-run，不是 installer
- `desktop` 不会自动启动 `relay`
- `desktop` 不会自动发现或安装远端 `remote-agent`
- `desktop` 不会替试用者补写远端 env
- 当前本地正式承诺平台仍是 Windows
- 当前列表与 detail 只反映 `relay` 仍保留在内存中的状态；`relay` 重启后不会自动恢复旧状态

## 当前不承诺

- installer
- `exe` / `msi`
- 代码签名
- 自动更新
- 独立桌面分发包
- 内置 relay bootstrap
- 非 Windows 正式交付承诺
