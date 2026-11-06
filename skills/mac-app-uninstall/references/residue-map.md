# macOS 应用残留位置地图

按「删的时候会不会心疼」排序——越靠前的越是纯垃圾，越靠后的越可能含不可恢复的东西。

匹配时用 bundle id（`com.vendor.App`），不是显示名。少数位置用的是 team id 前缀的变体（`TEAMID.com.vendor.App`）或另起的标识符（OrbStack 的 group container 叫 `HUAQ24HBR6.dev.orbstack`，跟它的 bundle id `dev.kdrag0n.MacVirt` 毫无关系）。

## 用户级（`~/Library/`，不需要 sudo）

| 位置 | 命名 | 装什么 | 删了会怎样 |
|---|---|---|---|
| `Caches/<bid>` | bundle id | 磁盘缓存 | 自动重建，随便删 |
| `Saved Application State/<bid>.savedState` | bundle id | 窗口位置、未保存的草稿 | 下次开窗口位置重置 |
| `HTTPStorages/<bid>` `<bid>.binarycookies` | bundle id | Cookie、HTTP 缓存 | 需要重新登录 |
| `WebKit/<bid>` | bundle id | 内嵌浏览器的数据 | 自动重建 |
| `Logs/<显示名>` 或 `Logs/<bid>` | 两种都有 | 日志 | 随便删 |
| `Preferences/<bid>.plist` | bundle id | 偏好设置 | **设置全丢**，重装后从头配 |
| `Preferences/ByHost/<bid>.<硬件UUID>.plist` | bundle id + 机器 UUID | 绑定本机的偏好（更新器状态等） | 同上。**这层子目录极易漏扫**——按 `Preferences` 一层扫是扫不到的 |
| `Application Scripts/<TEAMID>.<bid>` | team id 前缀 | 沙盒应用的脚本目录 | 通常是空的 |
| `Application Support/<显示名>` | **显示名**居多 | 应用主数据 | **可能含不可恢复数据** |
| `Containers/<bid>` | bundle id | 沙盒应用的全部数据 | **聊天记录、文档都在这** |
| `Group Containers/<TEAMID>.<bid>` | team id 前缀，也可能另起标识 | 应用组共享数据 | 同上 |

注意 `Application Support` 是少数**按显示名**命名的位置（`Application Support/Termius`、`Application Support/CherryStudio`），光按 bundle id 搜会漏。

## 开机代理（卸载不干净的头号原因）

| 位置 | 需要 sudo | 说明 |
|---|---|---|
| `~/Library/LaunchAgents/*.plist` | 否 | 登录时启动。**带 `KeepAlive` 的会让进程杀了就重生** |
| `/Library/LaunchAgents/*.plist` | 是 | 所有用户登录时启动 |
| `/Library/LaunchDaemons/*.plist` | 是 | 开机即启动，不需要登录 |
| `/Library/PrivilegedHelperTools/<bid>` | 是 | 特权助手二进制，配合 LaunchDaemon 用 |

删 plist 之前先 `launchctl bootout gui/$(id -u)/<label>`，否则 launchd 里的注册还在。

## 家目录隐藏目录（最容易漏）

不少应用（尤其是带 CLI 的）在家目录直接建点开头的目录，按 `~/Library` 扫一遍完全扫不到：

```
~/.<小写应用名>        实测：~/.workbuddy 369M、~/.orbstack 316K
~/.config/<小写名>
```

## 其他可能的位置

| 位置 | 什么情况下有 |
|---|---|
| `~/Library/Fonts/` | 字体管理类应用装的字体。**卸载应用不会删这些字体，它们是独立文件，其他 App 还在用** |
| `~/Library/Internet Plug-Ins/` | 浏览器插件 |
| `~/Library/QuickLook/` | QuickLook 预览扩展 |
| `~/Library/Services/` | 服务菜单项 |
| `/Library/Application Support/<厂商>` | 需 sudo，多为共享组件（驱动、VPN 客户端） |
| `/Library/Extensions`、系统扩展 | 需 sudo，卸载前要先在「系统设置 → 登录项与扩展」里禁用 |

## 钥匙串：不删，但要告诉用户

应用存在钥匙串里的密码、令牌、SSH 私钥**不会随卸载消失**，`security find-generic-password -s <服务名>` 能查到。

**不要自动删钥匙串条目**：条目和应用的对应关系不可靠（多个应用可能共用一个服务名），删错了是不可恢复的凭据丢失。正确做法是在报告里提一句「钥匙串里还有 N 条相关记录，需要的话在钥匙串访问里自行清理」，把判断留给用户。CleanMyMac 也是这么处理的。

## 删不掉是正常的那一类

`~/Library/Containers/<bid>/` 下的 `.com.apple.containermanagerd.metadata.plist` 受 SIP 保护，`rm` 报 `Operation not permitted`。内容能删，外壳留几 KB。这不是失败，不用想办法绕过——绕过要关 SIP，代价远超收益。
