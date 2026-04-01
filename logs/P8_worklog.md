# P8 Worklog

Updated: 2026-04-01

## 当前状态

- 当前阶段：`P8 V1.0 Release`
- 当前子目标：`P8 V1 Scope Freeze And Release Surface Audit`
- 前序阶段：`P7 Local Session Interaction UI` 已完成
- 下一阶段：`P9 Codex Support`

## 本轮目标

- 以当前 repo 实际能力为准，统一 `v1.0` 对外口径
- 冻结 `v1.0` 已承诺能力与未承诺能力
- 收口 README、DEV、Quick Start、trial / release / checklist 文档
- 明确 `P6.5` 文档与当前 `P8 v1.0` 文档的关系
- 输出 blocker 审计结果

## 本轮审计文档

- `README.md`
- `DEV.md`
- `logs/P8_worklog.md`
- `logs/P6.5_trial_guide.md`
- `logs/P6.5_release_notes.md`
- `logs/P6.5_launch_checklist.md`
- `desktop/README.md`
- `remote-agent/README.md`

## 本轮对照的实现入口

- `relay/main.py`
- `relay/remote_agent_client.py`
- `remote-agent/src/remote_agent/app.py`
- `remote-agent/src/remote_agent/cli.py`
- `remote-agent/scripts/install-systemd-user.sh`
- `desktop/package.json`
- `desktop/src/renderer/app.js`
- `desktop/src/renderer/state/snapshot-store.js`
- `desktop/src/renderer/features/sessions/render-session-detail.js`
- `desktop/src/renderer/features/approvals/render-approval-list.js`

## 审计结论

### 1. 当前 `v1.0` 已真实支持

- 本地 Windows source-run `desktop`
- 本地 operator-run `relay`
- 远端 Linux `remote-agent`
- `Kimi --wire` hosted session 启动
- multi-remote 聚合
- approval 以 `remote_id + request_id` 唯一定位
- 本地 session list
- 本地 session detail / recent transcript
- 本地 UI 提交 `reply`
- 本地 UI 处理 `approve / reject`
- 远端 `remote-agent sessions / watch / reply / stop`

### 2. 当前不支持，且不能写成 `v1.0` 已支持

- `P9 Codex Support`
- `P10` reconnect
- `P10` checkpoint / replay
- `P10` pending approvals replay
- `P10` `remote-agent` 重启恢复
- `P10` provider 执行现场恢复
- `V2 Claude`
- `attach`
- 通用聊天工作台
- token 流透传
- 推理链可视化
- installer / 云服务 / 多设备 / 账号体系

### 3. `P6.5` 文档与 `P8` 的关系

- `logs/P6.5_trial_guide.md`
  - 历史文件名保留
  - 当前升级为 `v1.0` operator-led 最小试用指南
- `logs/P6.5_release_notes.md`
  - 历史文件名保留
  - 当前升级为 `v1.0` release surface 说明
- `logs/P6.5_launch_checklist.md`
  - 历史文件名保留
  - 当前升级为 `v1.0` release surface checklist

结论：

- `P6.5` 阶段本身是历史阶段
- 这三份文件不再代表“项目仍停留在 Beta”
- 这三份文件当前继续存在，但内容必须跟随 `P8 v1.0` 口径同步

## blocker 审计结果

### Release-blocking

- 本轮未识别出一个需要立刻修改 `relay/`、`desktop/` 或 `remote-agent/`
  实现，才能让当前 `v1.0` 文档成立的 confirmed code blocker
- 本轮没有执行真实远端完整链路复跑，因此“未发现 confirmed blocker”
  不等于“已做 live E2E 验证并完全排除实现风险”

### Non-blocking but must stay documented

- `desktop` 仍是 source-run，不是 installer
- `relay` 仍需手工启动
- `remote-agent` 仍需手工补 env
- 本地与远端网络检查仍需手工完成
- 当前唯一正式 provider 是 `Kimi`
- 本地正式承诺平台是 Windows；远端正式承诺平台是 Linux
- `watch` 是单次读取
- `attach` 未实现
- `stop` 不能在 `approval_pending` 或 turn 运行中执行
- `relay` 与 `remote-agent` 都仍是内存态

### Doc-only issues

- README 仍保留 `P7` 之前的旧限制表述
- README 与 P6.5 文档对 `logs/` 下文件的引用路径不统一
- `logs/P6.5_trial_guide.md` 把阶段状态写成 `P7 Codex Support`
- `logs/P6.5_release_notes.md` 把下一阶段写成 `P7 Codex Support`
- `logs/P6.5_launch_checklist.md` 把下一阶段写成 `P7 Codex Support`
- `desktop/README.md` 只写了 approval 观察面，没有同步 `session detail + reply`
- `remote-agent/README.md` 仍按 `P4/P4.5` 与首发 Beta 口径表述，没有同步当前 `P8`

## 本轮统一后的最小试用路径

1. 本地启动 `relay`
2. 本地启动 `desktop`
3. 远端安装并启动 `remote-agent`
4. 远端启动一个 `Kimi` hosted session
5. 在本地 UI 中看到 session 并打开 detail
6. 在本地 UI 中提交一轮 `reply`
7. 在本地 UI 中处理一轮 approval

推荐用于验证 `reply -> approval` 闭环的 UI reply：

```text
Create a file named acp-v1-proof.txt in the current directory, but ask for approval before writing anything.
```

## 本轮修改结论

- 当前阶段仍停留在 `P8`
- 当前子目标 `P8 V1 Scope Freeze And Release Surface Audit` 在文档层面完成
- 当前没有因为本轮审计而前推到 `P9`
- 如需进一步降低发布风险，下一轮应做真实远端完整链路验证或针对验证结果补最小实现修复
