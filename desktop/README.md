# desktop

For an operator-led 2-5 person Beta trial, pair this file with the root
`P6.5_trial_guide.md`. This readme defines the local desktop boundary and local
runtime steps only.

`desktop/` 是首发公开 Beta 的本地桌面控制端壳层。

当前 `P6.5-2 Desktop Delivery Baseline` 固定如下：
- 交付形态：repo 内 source-run 目录
- 首发本地平台：Windows
- 启动命令：`cd desktop`、`npm install`、`npm start`
- 当前脚本面：`package.json` 只提供 `start` 与 `dev`
- 当前不包含：build、package、installer、签名包、自动更新

## 最小依赖
- Node.js 与 npm
- 仓库副本
- 一个已启动且可访问的本地 `relay`

## relay 连接假设
- 默认连接 `http://127.0.0.1:8000`
- 如需覆盖，通过 `RELAY_BASE_URL` 在当前 shell 中显式指定
- `desktop` 只消费 `relay` snapshot 与 approval API
- `desktop` 不负责自动启动 `relay`

## 首发公开 Beta 最小本地试用路径

`desktop` 在首发公开 Beta 中只承担本地观察与审批职责，不承担
`relay` 自动拉起、远端 `remote-agent` 安装，或 `Kimi` provider 安装。

### 本地 Windows 步骤

1. 在 repo 根目录安装并启动本地 `relay`：

```powershell
python -m pip install -r requirements-relay.txt
python -m uvicorn relay.main:app --host 127.0.0.1 --port 8000
```

2. 可选验证本地 `relay` 已响应：

```powershell
curl.exe http://127.0.0.1:8000/v1/snapshot
```

3. 打开第二个本地 shell，启动 `desktop`：

```powershell
cd desktop
npm install
npm start
```

4. 保持 `desktop` 窗口打开，等待远端 `remote-agent` 上报 session 与
   approval。

5. 当 pending approvals 列表中出现请求时，点击 `Approve` 或 `Reject`。

### 本地可见结果

- session 列表显示 `relay` 当前 snapshot 中的 hosted sessions
- pending approvals 列表显示待处理 approval 请求
- 每条 approval 当前提供 `Approve` 与 `Reject` 按钮
- 本地决策会先提交给 `relay`，再由 `relay` 回写到对应远端
  `remote-agent`

### 本地边界

- `desktop` 不会自动启动 `relay`
- `desktop` 不会自动发现或安装远端 `remote-agent`
- `desktop` 不会替试用者补写远端 env
- 当前列表只反映 `relay` 仍保留在内存中的 session / approval；`relay`
  重启后不会自动恢复旧状态

## 为什么首发 Beta 仍接受 source-run
- 首发公开 Beta 面向技术试用者
- 当前验证重点是控制面流程，而不是安装分发体验
- 当前还没有正式的桌面打包与发布链路
- 在没有稳定 installer 之前，source-run 比伪装成“已可分发”更真实

## 当前不承诺
- installer
- `exe` / `msi`
- 代码签名
- 自动更新
- 独立桌面分发包
- 内置 relay bootstrap
