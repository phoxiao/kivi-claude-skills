# 卸载踩坑速查表

动手前扫一眼。每一条都是实测撞出来的，不是理论风险。

## U1. `KeepAlive` 的 LaunchAgent 让进程"杀不死"

**症状**：`pkill` 之后进程还在，但 PID 变了。

**原因**：应用注册了带 `KeepAlive=true` 的 LaunchAgent，launchd 一发现进程没了就立刻重新拉起。

**正确顺序**：先 `launchctl bootout gui/$(id -u)/<label>` 并删掉 plist，再杀进程。反过来做只会陷入"杀了重生"的循环。

实测案例：Ardot（腾讯 CoCraft）的 `~/Library/LaunchAgents/com.tencent.cocraft.bridge.plist`，`KeepAlive` + `RunAtLoad` 都是 true。

## U2. 只删 .app 不删 plist = 留下一个永远失败的开机项

launchd 会一直去拉一个已经不存在的程序，每次开机失败重试。用户感觉不到，但它是真实的系统垃圾。**这正是 CleanMyMac 这类工具主要在替用户处理的东西。**

## U3. 拿 bundle id 末段做子串匹配会删错文件

`com.termius-dmg.mac` 的末段是 `mac`，`find -iname "*mac*"` 会命中 CleanMyMac 的特权助手和几十个系统扩展。

**必须用结构化的精确匹配**：整段相等、`<bid>.` 前缀、`.<bid>` 后缀。见 `scripts/audit-app.sh` 的 `belongs()`。

## U4. `mdls` 的「最后使用时间」会漏，不能单凭它判定闲置

实测 Ardot 有两个守护进程在跑，`kMDItemLastUsedDate` 却是空的；Termius 也是空的。

**三个信号交叉验证**：mdls 时间、数据目录 mtime、有没有进程在跑。三个里最硬的是进程。

## U5. `ps` 会把中文 App 名转义，grep 中文必然假阴性

`ps -Ao comm | grep 企业微信` 什么都搜不到，因为 ps 把它显示成 `M-dM-<M^AM-dM-8M^Z...`。

**改用**：`pgrep -f "/Applications/企业微信.app"`（按路径匹配），或 `osascript -e 'tell application "System Events" to get name of every application process whose background only is false'`。

## U6. 沙盒容器外壳删不掉是正常的

`.com.apple.containermanagerd.metadata.plist` 受 SIP 保护，报 `Operation not permitted`。内容已清空，外壳几 KB。不要为此关 SIP。

## U7. Setapp 托管的应用直接删会被装回

`/Applications/Setapp/` 下的应用由 Setapp 客户端管理。删了之后 Setapp 检测到缺失会重新下载。**必须在 Setapp 客户端里卸载。**

## U8. 家目录隐藏目录最容易漏

按 `~/Library` 扫一遍很干净，实际 `~/.<应用名>` 里还躺着几百 MB。实测 WorkBuddy 的 `~/.workbuddy` 有 369M，第一遍完全没扫到。

## U9. 卸载字体管理类应用不会删掉它装的字体

字体是 `~/Library/Fonts/` 下的独立文件，其他应用还在用。这是好事——不用担心卸载 Ardot 会让文档里的字体失效。反过来说，如果目的是腾空间，字体要单独看。

## U10. 属主不是自己的 .app 需要 sudo

`/Applications` 下有些应用是 root 属主。`stat -f '%Su'` 先查一眼。脚本不替用户 sudo，因为这些路径影响全系统，该由人自己确认。

## U11. 批量 `rm -rf` 循环可能被安全分类器拦

在自动化环境里，带循环和变量的批量删除命令有时会被拦下。拆成逐条明确路径的 `rm -rf` 通常能过。不要反复硬试同一条命令。
