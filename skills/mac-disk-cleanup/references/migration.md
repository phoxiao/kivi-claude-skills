# Step 3c 迁移的关键决策

迁移比删除风险高——它改变 App 读写路径。做对这几个决策，迁移才不会在下次更新/重启后失效或损坏数据。

## 决策一：三种方式怎么选

优先级从高到低，能用上面的就别用下面的：

1. **官方设置改数据路径** —— 应用自带「数据目录」配置（OrbStack `data_dir`、LM Studio 模型目录、Docker Desktop disk image location 等）。应用自己管理路径，完全没有软链风险。**永远先查有没有这个。**

2. **软链迁移** —— 应用没有官方设置，但数据可以整体挪走并用符号链接指回。需要外置盘**常年连接**。适合 Electron 大数据目录、无配置项的 VM 镜像等。

3. **直接移动** —— 纯归档文件，`mv` 到外置盘，不软链（软链只会掩盖真实位置，让人忘了文件真在哪）。

## 决策二：软链设在哪一层（最容易出错）

软链失效的唯一场景：某进程对**软链本身**做 `rename()` 或「删目录再 mkdir」。所以要把软链设在应用**不会整体重建的那一层**。

判断方法——观察目录内文件的时间戳：
```bash
ls -la <candidate-dir>/          # 看里面哪些文件时间戳老、哪些常变
stat -f "%Sm %N" -t "%m-%d %H:%M" <dir>/*
```
如果目录里有**长期不变的标识文件**（如 `machineIdentifier`、`macAddress`），说明应用从不整体重建这个目录，只改内部的内容文件——**这一层适合做软链目标**。

反过来，如果某层目录会被应用整个删掉重建，就把软链设在**它的父层**：应用删的是软链**内部**的子目录（在外置盘删了重建，软链保持有效），而不是软链本身。

> 案例：Claude Desktop 的 `vm_bundles`。更新器（Squirrel/ShipIt）只替换 `/Applications/Claude.app`，从不碰 `~/Library/Application Support/Claude/`（可查 `ShipItState.plist` 的 `targetBundleURL`）；VM 镜像刷新是对 `claudevm.bundle/rootfs.img` 这个**文件**做读写（`machineIdentifier` 半年没变可证），透明穿过软链。所以软链设在 `vm_bundles` 外层目录安全，别设在里面的 `claudevm.bundle`。

自检：迁移后 `readlink <path>` 有输出（指向外置盘）就是软链存活、迁移有效。

## 决策三：沙盒容器只软链内层

沙盒 App（微信、企业微信等）的容器根目录带 `containermanagerd` 的 metadata plist，会被校验。**软链容器根 → 大概率触发容器重建（聊天记录丢失）或拒绝启动。**

正确做法：只软链内层 `Data/Documents`（大头通常在此）：
```bash
# 先完全退出 App；先 cp -Rp 备份 Documents 到外置盘另一位置
mv   ~/Library/Containers/<id>/Data/Documents  /Volumes/EXT/Offloaded/<app>-Documents
ln -s /Volumes/EXT/Offloaded/<app>-Documents   ~/Library/Containers/<id>/Data/Documents
```
沙盒对容器内**子目录**的软链容忍度远高于容器根。验证：启动 App，登录、历史记录完整、收发新消息且重启后仍在。任一不满足立即回滚。

## 决策四：owners 红线

外置盘 `Owners: Disabled` 时**不要** `diskutil enableOwnership`——见 pitfalls M1，可能导致整盘不可读。保持 Disabled 的代价：只迁不依赖权限位的数据。不要迁 `~/.ssh`、`~/.gnupg`、GPG/SSH 密钥、依赖 0600/0700 的配置目录。单用户环境下这些本就不需要挪，且它们通常也不是占用大头。

## 通用安全动作

- **动任何 App 数据前，完全退出该 App**（`osascript -e 'quit app "X"'` 后确认进程真的退了）。Electron 应用有时不响应 AppleScript quit，需手动退或确认无未保存状态后处理。
- **高风险项（沙盒容器、聊天记录）先 `cp -Rp` 备份再动手。**
- **删源前，用 `rsync -an --checksum` 确认逐文件一致**（见 pitfalls M5）。
- **迁移后重启一次验证**（挂载竞态，pitfalls M7）。
