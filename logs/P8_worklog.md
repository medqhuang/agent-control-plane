# P8 Worklog

Updated: 2026-04-01

## 褰撳墠鐘舵€?
- 褰撳墠闃舵锛歚P8 V1.0 Release`
- 褰撳墠瀛愮洰鏍囷細`P8 Live End-to-End Trial Verification And Blocker Triage`
- 鍓嶅簭闃舵锛歚P7 Local Session Interaction UI` 宸插畬鎴?- 涓嬩竴闃舵锛歚P9 Codex Support`

## 鏈疆鐩爣

- 浠ュ綋鍓?repo 瀹為檯鑳藉姏涓哄噯锛岀粺涓€ `v1.0` 瀵瑰鍙ｅ緞
- 鍐荤粨 `v1.0` 宸叉壙璇鸿兘鍔涗笌鏈壙璇鸿兘鍔?- 鏀跺彛 README銆丏EV銆丵uick Start銆乼rial / release / checklist 鏂囨。
- 鏄庣‘ `P6.5` 鏂囨。涓庡綋鍓?`P8 v1.0` 鏂囨。鐨勫叧绯?- 杈撳嚭 blocker 瀹¤缁撴灉

## 鏈疆瀹¤鏂囨。

- `README.md`
- `DEV.md`
- `logs/P8_worklog.md`
- `logs/P6.5_trial_guide.md`
- `logs/P6.5_release_notes.md`
- `logs/P6.5_launch_checklist.md`
- `desktop/README.md`
- `remote-agent/README.md`

## 鏈疆瀵圭収鐨勫疄鐜板叆鍙?
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

## 瀹¤缁撹

### 1. 褰撳墠 `v1.0` 宸茬湡瀹炴敮鎸?
- 鏈湴 Windows source-run `desktop`
- 鏈湴 operator-run `relay`
- 杩滅 Linux `remote-agent`
- `Kimi --wire` hosted session 鍚姩
- multi-remote 鑱氬悎
- approval 浠?`remote_id + request_id` 鍞竴瀹氫綅
- 鏈湴 session list
- 鏈湴 session detail / recent transcript
- 鏈湴 UI 鎻愪氦 `reply`
- 鏈湴 UI 澶勭悊 `approve / reject`
- 杩滅 `remote-agent sessions / watch / reply / stop`

### 2. 褰撳墠涓嶆敮鎸侊紝涓斾笉鑳藉啓鎴?`v1.0` 宸叉敮鎸?
- `P9 Codex Support`
- `P10` reconnect
- `P10` checkpoint / replay
- `P10` pending approvals replay
- `P10` `remote-agent` 閲嶅惎鎭㈠
- `P10` provider 鎵ц鐜板満鎭㈠
- `V2 Claude`
- `attach`
- 閫氱敤鑱婂ぉ宸ヤ綔鍙?- token 娴侀€忎紶
- 鎺ㄧ悊閾惧彲瑙嗗寲
- installer / 浜戞湇鍔?/ 澶氳澶?/ 璐﹀彿浣撶郴

### 3. `P6.5` 鏂囨。涓?`P8` 鐨勫叧绯?
- `logs/P6.5_trial_guide.md`
  - 鍘嗗彶鏂囦欢鍚嶄繚鐣?  - 褰撳墠鍗囩骇涓?`v1.0` operator-led 鏈€灏忚瘯鐢ㄦ寚鍗?- `logs/P6.5_release_notes.md`
  - 鍘嗗彶鏂囦欢鍚嶄繚鐣?  - 褰撳墠鍗囩骇涓?`v1.0` release surface 璇存槑
- `logs/P6.5_launch_checklist.md`
  - 鍘嗗彶鏂囦欢鍚嶄繚鐣?  - 褰撳墠鍗囩骇涓?`v1.0` release surface checklist

缁撹锛?
- `P6.5` 闃舵鏈韩鏄巻鍙查樁娈?- 杩欎笁浠芥枃浠朵笉鍐嶄唬琛ㄢ€滈」鐩粛鍋滅暀鍦?Beta鈥?- 杩欎笁浠芥枃浠跺綋鍓嶇户缁瓨鍦紝浣嗗唴瀹瑰繀椤昏窡闅?`P8 v1.0` 鍙ｅ緞鍚屾

## blocker 瀹¤缁撴灉

### Release-blocking

- 鏈疆鏈瘑鍒嚭涓€涓渶瑕佺珛鍒讳慨鏀?`relay/`銆乣desktop/` 鎴?`remote-agent/`
  瀹炵幇锛屾墠鑳借褰撳墠 `v1.0` 鏂囨。鎴愮珛鐨?confirmed code blocker
- 鏈疆娌℃湁鎵ц鐪熷疄杩滅瀹屾暣閾捐矾澶嶈窇锛屽洜姝も€滄湭鍙戠幇 confirmed blocker鈥?  涓嶇瓑浜庘€滃凡鍋?live E2E 楠岃瘉骞跺畬鍏ㄦ帓闄ゅ疄鐜伴闄┾€?
### Non-blocking but must stay documented

- `desktop` 浠嶆槸 source-run锛屼笉鏄?installer
- `relay` 浠嶉渶鎵嬪伐鍚姩
- `remote-agent` 浠嶉渶鎵嬪伐琛?env
- 鏈湴涓庤繙绔綉缁滄鏌ヤ粛闇€鎵嬪伐瀹屾垚
- 褰撳墠鍞竴姝ｅ紡 provider 鏄?`Kimi`
- 鏈湴姝ｅ紡鎵胯骞冲彴鏄?Windows锛涜繙绔寮忔壙璇哄钩鍙版槸 Linux
- `watch` 鏄崟娆¤鍙?- `attach` 鏈疄鐜?- `stop` 涓嶈兘鍦?`approval_pending` 鎴?turn 杩愯涓墽琛?- `relay` 涓?`remote-agent` 閮戒粛鏄唴瀛樻€?
### Doc-only issues

- README 浠嶄繚鐣?`P7` 涔嬪墠鐨勬棫闄愬埗琛ㄨ堪
- README 涓?P6.5 鏂囨。瀵?`logs/` 涓嬫枃浠剁殑寮曠敤璺緞涓嶇粺涓€
- `logs/P6.5_trial_guide.md` 鎶婇樁娈电姸鎬佸啓鎴?`P7 Codex Support`
- `logs/P6.5_release_notes.md` 鎶婁笅涓€闃舵鍐欐垚 `P7 Codex Support`
- `logs/P6.5_launch_checklist.md` 鎶婁笅涓€闃舵鍐欐垚 `P7 Codex Support`
- `desktop/README.md` 鍙啓浜?approval 瑙傚療闈紝娌℃湁鍚屾 `session detail + reply`
- `remote-agent/README.md` 浠嶆寜 `P4/P4.5` 涓庨鍙?Beta 鍙ｅ緞琛ㄨ堪锛屾病鏈夊悓姝ュ綋鍓?`P8`

## 鏈疆缁熶竴鍚庣殑鏈€灏忚瘯鐢ㄨ矾寰?
1. 鏈湴鍚姩 `relay`
2. 鏈湴鍚姩 `desktop`
3. 杩滅瀹夎骞跺惎鍔?`remote-agent`
4. 杩滅鍚姩涓€涓?`Kimi` hosted session
5. 鍦ㄦ湰鍦?UI 涓湅鍒?session 骞舵墦寮€ detail
6. 鍦ㄦ湰鍦?UI 涓彁浜や竴杞?`reply`
7. 鍦ㄦ湰鍦?UI 涓鐞嗕竴杞?approval

鎺ㄨ崘鐢ㄤ簬楠岃瘉 `reply -> approval` 闂幆鐨?UI reply锛?
```text
Create a file named acp-v1-proof.txt in the current directory, but ask for approval before writing anything.
```

## 鏈疆淇敼缁撹

- 当前阶段仍停留在 `P8`
- `P8 V1 Scope Freeze And Release Surface Audit` 已完成，文档状态已同步前推到 `P8 Live End-to-End Trial Verification And Blocker Triage`
- 当前没有因为本轮审计而前推到 `P9`；如需进一步降低发布风险，下一轮应做真实远端完整链路验证或针对验证结果补最小实现修复
