---
name: mac-app-uninstall
description: macOS 应用的彻底卸载——把 App 本体、散落在十来处的数据残留、以及会让进程"杀不死"的开机代理一并清干净，而不是把 .app 拖进废纸篓了事。当用户说「卸载 XX / 删掉这个软件 / 清理没用的应用 / 哪些软件可以卸 / uninstall / 这个 App 卸干净了吗 / 卸载残留」时使用；也在用户为了腾磁盘空间而问「有哪些软件可以删」时使用——本 skill 自带按大小和最后使用时间排序的应用盘点。macOS 专用。只是想知道某个 App 是干什么的、或者只要禁用开机启动不卸载，不用它。
---

# macOS 应用彻底卸载

把 `.app` 拖进废纸篓，通常只清掉了不到一半。剩下的散在 `~/Library` 十来个子目录里，还有可能留下一个每次开机都尝试拉起已不存在程序的 launchd 代理。这个 skill 做的就是 CleanMyMac 卸载器真正有价值的那部分：**找全**，然后**按正确顺序删**。

四步：**盘点 → 审计 → 卸载 → 复查**。

---

## 核心方法：bundle id 才是钥匙

找残留时最容易犯的错，是拿 App 的显示名去搜 `~/Library`。这对相当一部分应用完全无效：

| 显示名 | bundle id | 残留目录实际叫什么 |
|---|---|---|
| OrbStack | `dev.kdrag0n.MacVirt` | `Caches/dev.kdrag0n.MacVirt`、`Group Containers/HUAQ24HBR6.dev.orbstack` |
| Ardot | `com.tencent.cocraft` | 按 "ardot" 只搜得到日志目录 |
| Termius | `com.termius-dmg.mac` | `Preferences/com.termius-dmg.mac.plist` |

所以先取 bundle id：

```bash
plutil -extract CFBundleIdentifier raw "/Applications/名字.app/Contents/Info.plist"
```

**但反过来也有陷阱：绝不能拿 bundle id 的末段做子串匹配。** `com.termius-dmg.mac` 的末段是 `mac`，用它去 `find -iname "*mac*"` 会命中 CleanMyMac 的特权助手和几十个系统扩展——这个 bug 在本 skill 第一版真实发生过，接到删除逻辑上就是删错文件。

`scripts/audit-app.sh` 里的 `belongs()` 用的是结构化的精确匹配（整段相等、前缀带点、后缀带点），不做模糊子串。要改匹配逻辑，两个脚本里各有一份，必须同步改。

---

## 第 1 步：盘点（用户问「有哪些能卸」时）

```bash
scripts/audit-app.sh --all
```

输出所有应用的大小、最后使用时间、属主，按大小排序。

**「最后使用」为 `-` 不等于没用过。** `mdls` 的 `kMDItemLastUsedDate` 记录很不全——实测 Ardot 明明有两个进程在后台跑，这个字段却是空的；Termius 也是空的。单凭它下结论会把在用的应用判成闲置。

判断一个应用是否真的闲置，要三个信号交叉验证：

1. `mdls` 的最后使用时间（有就参考，没有不代表没用）
2. **数据目录的最后修改时间**（更可靠，但后台进程也会碰它，所以是上界）
3. **有没有进程在跑**（最硬的信号）

`audit-app.sh <名字>` 会把这三个一起给出。

盘点时要提醒用户的两件事：
- `/Applications/Setapp/` 下的应用**必须在 Setapp 客户端里卸载**，直接删会被自动装回
- 一年用两次但用时非它不可的小工具（SSH 客户端、远程桌面、抓包工具），省几百 MB 不值得卸

---

## 第 1.5 步：筛选界面（应用多、要挑的时候）

命令行清单超过二三十行就不好挑了。这时候生成一个可筛选的网页：

```bash
scripts/scan-all.py /tmp/apps.json      # 扫描，约 2-3 分钟
scripts/build-ui.sh /tmp/apps.json ui.html
```

`ui.html` 是自包含的，浏览器打开即可，也可以发布成 Artifact 让用户在手机上挑。界面提供按占用/闲置时长排序、多条件筛选（闲置 90 天以上、占用 ≥500MB、当前未运行等）、勾选后实时算合计，并生成对应的卸载命令。

**网页不执行删除**，只负责「挑」。Setapp 托管和非当前用户属主的应用在界面里是禁选的，鼠标悬停会说明原因。实际删除仍走 `uninstall-app.sh`，所有守卫都在那里——把删除权限锁在一个经过审查的脚本里，界面只做选择，是刻意的切分。

`scan-all.py` 为什么是 Python 而不是 shell：第一版 shell 实现按「每个应用 × 每个位置」各跑一次 `du`，把 `~/Library/Containers` 重复遍历几十遍，50 个应用要十几分钟。现在每个基础目录只 `du` 一遍建索引再匹配，约 2-3 分钟。

## 第 2 步：审计单个应用

```bash
scripts/audit-app.sh "Discord"
scripts/audit-app.sh --id com.hnc.Discord    # .app 已删、只清残留时
```

输出四块：应用信息、运行中的进程、开机代理、数据残留（含合计大小）。

**看到「有开机代理」且标着 `KeepAlive` 时要格外注意**——那意味着直接杀进程是杀不死的，见下一步的顺序说明。

残留会藏在哪些位置，完整地图在 `references/residue-map.md`。

---

## 第 3 步：卸载

```bash
scripts/uninstall-app.sh "Discord"              # 默认预演，只列不删
scripts/uninstall-app.sh "Discord" --execute    # 真删
```

**默认预演是刻意的。** 卸载不可逆，应用的授权文件、许可证、本地配置都在数据目录里。把「看清单」和「按下删除」分成两次动作，是为了给判断留位置。跑完预演，把清单给用户看过再 `--execute`。

### 顺序为什么是这个顺序

脚本按这个顺序执行，反了会出问题：

1. **先卸载并删除 LaunchAgent / LaunchDaemon**
2. 再优雅退出应用（`osascript quit`）
3. 再强制终止残留进程
4. 然后删 `.app` 本体
5. 最后删数据目录

**顺序反了的后果**（实测踩过）：Ardot 的 LaunchAgent 写着 `KeepAlive=true` + `RunAtLoad=true`。先 `pkill` 的话 launchd 立刻重新拉起，PID 变了但进程还在，看起来像"杀不死"。必须先把 plist `bootout` 掉并删除，守护没了才杀得干净。

反过来，**只删 `.app` 不删 plist**，launchd 会一直去拉一个不存在的程序，每次开机失败重试——这是"卸载了但没卸干净"最常见的形态，也是 CleanMyMac 这类工具真正在替用户处理的东西。

### 需要 sudo 的部分

`/Library/LaunchAgents`、`/Library/LaunchDaemons`、`/Library/PrivilegedHelperTools` 下的文件，以及属主不是当前用户的 `.app`，脚本**只报告不动手**，会打印出对应的 `sudo rm` 命令交给用户执行。不替用户 sudo 是有意的——这些路径影响全系统。

---

## 第 4 步：复查

`--execute` 跑完脚本会自动复查：`.app` 没了、进程没了、代理没了。

**有一类"残留"是正常的，不要当成失败**：沙盒应用的容器外壳删不掉。`~/Library/Containers/<bundle-id>/` 下有个 `.com.apple.containermanagerd.metadata.plist` 受 SIP 保护，`rm` 会报 `Operation not permitted`。内容已经清空，剩下的外壳只有几 KB，可以忽略。

---

## 沟通基调

这是不可逆操作。始终：

- **先出清单再动手。** 预演的输出要完整贴给用户看，不要自己判断"这些明显该删"就跳过确认。
- **说清楚删了会失去什么。** 数据目录里可能有许可证、账号配置、本地数据库。对付费软件尤其要提。
- **发现应用在运行时停下来问。** 进程在跑说明它不是闲置的，用户可能忘了自己在用。这次实测 Ardot 就是——`mdls` 显示"从未使用"，实际两个守护进程一直在后台跑。
- **如实报告没做完的部分。** 需要 sudo 的、SIP 拦住的、Setapp 托管的，都要明说哪些没清、为什么。

---

## 配套资源

**脚本（`scripts/`）**
- `audit-app.sh` — 只读审计。`--all` 盘点全部应用；`<名字>` 或 `--id <bundle-id>` 审计单个
- `uninstall-app.sh` — 执行卸载。默认预演，`--execute` 才真删
- `scan-all.py` — 全量扫描产出 JSON 快照（只读）
- `build-ui.sh` — 把快照注入模板，生成可筛选的自包含网页

**模板（`assets/`）**
- `uninstaller.html` — 筛选界面模板，`__DATA__` 和 `__ME__` 两个占位符由 build-ui.sh 替换

**参考（`references/`，按需读取）**
- `residue-map.md` — 残留位置完整地图，以及每个位置装的是什么
- `pitfalls.md` — 踩坑速查表，动手前值得扫一眼
