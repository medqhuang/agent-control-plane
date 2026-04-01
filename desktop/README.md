# desktop

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
