# Agent Control Plane Developer README

面向维护者与实现者的仓库说明。当前阶段控制、路线基线与验收口径仍以
[DEV.md](DEV.md) 为准；本文件补充仓库结构、发布面与当前已验证能力。

## Status

- 当前阶段：`P9 Codex Support`
- 已完成发布闸门：`P8 V1.0 Release`
- 当前唯一已真实验证通过的 provider：`Kimi`
- 下一阶段：`P10 Reliability Reinforcement`

## Fixed Architecture

`desktop -> relay -> remote-agent -> provider native interface`

## v1.0 Release Surface

- 本地 Windows source-run `desktop`
- 本地 operator-run `relay`
- 远端 Linux `remote-agent` + `systemd --user`
- `Kimi --wire` hosted session 主链路
- multi-remote 聚合
- approval 按 `remote_id + request_id` 唯一定位
- 本地 session list / detail / recent transcript
- 本地 UI `reply`
- 本地 UI `approve / reject`

## Not In v1.0

- `P9 Codex Support`
- `P10` reconnect / checkpoint / replay / pending approvals replay
- `P10` `remote-agent` 重启恢复
- provider `resume / reattach`
- `V2 Claude`
- `attach`
- 通用聊天工作台
- token 流透传
- installer / 云 relay / 多设备 / 账号体系

## Minimal Trial Path

1. 本地启动 `relay`
2. 本地启动 `desktop`
3. 远端安装并启动 `remote-agent`
4. 远端启动一个 `Kimi` hosted session
5. 在本地 UI 中看到 session 并打开 detail
6. 在本地 UI 中提交一轮 `reply`
7. 在本地 UI 中处理一轮 approval

推荐验证 `reply -> approval` 闭环的文案：

```text
Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.
```

## Verified P8 Gate

`P8 V1.0 Release` live gate 已真实通过，验证链路包括：

- 本地 relay 可被远端访问
- 远端控制面可被本地回控
- 远端 `remote-agent` 安装、启动与 `Kimi` hosted session 启动
- 本地 UI session visible / detail 打开
- 本地 UI `reply` 提交
- 本地 UI `approval` 提交
- `approval` 后 session 继续执行并回流到 detail

发布闸门中确认并修复过一个 blocker：

- `remote-agent kimi start` 在 service mode 下省略 `--workdir` 时未正确继承
  CLI 当前目录
- 当前仓库中的 [remote-agent/src/remote_agent/cli.py](remote-agent/src/remote_agent/cli.py)
  已修复为默认发送 `os.getcwd()`

## Known Limitations

- 当前正式 provider 只有 `Kimi`
- 正式承诺平台为本地 Windows + 远端 Linux
- `desktop` 仍是 source-run，不是 installer
- `relay` 仍需手工启动
- `remote-agent` 仍需手工补充 relay / control / remote-name env
- `watch` 当前是单次读取，不是持续 follow
- `attach` 当前未实现
- `stop` 当前不能在 `approval_pending` 或 turn 运行中执行
- `relay` 与 `remote-agent` 仍是内存态
- 当前不承诺 checkpoint、replay、pending approvals replay 或 provider `resume / reattach`

## Repo Pointers

- [README.md](README.md): GitHub 对外首页
- [DEV.md](DEV.md): 当前阶段、拆任务、验收基线
- [desktop/README.md](desktop/README.md): 本地桌面端说明
- [remote-agent/README.md](remote-agent/README.md): 远端托管端说明
- [logs/P9_worklog.md](logs/P9_worklog.md): 当前阶段工作记录
- [logs/P8_worklog.md](logs/P8_worklog.md): 上一阶段发布闸门记录
