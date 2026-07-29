# 踩坑速查表

部署定时任务、做迁移前先扫一遍这张表。每一条都是实战踩过、会让操作静默失败或数据受损的真坑。

## launchd 定时任务部署

| # | 症状 | 根因 | 解法 |
|---|------|------|------|
| **L1** | `launchctl bootstrap` 报 `Bootstrap failed: 5: Input/output error` | launchd **拒绝 `~/Library/LaunchAgents` 下的软链 plist**，必须是真实文件 | `cp` 而非 `ln -s`，`chmod 644`。所以 install 脚本要「拷贝」源码到运行位置，不能软链 |
| **L2** | launchd 跑脚本报 `Operation not permitted`，`last exit code = 126`，但同一脚本在终端里跑得好好的 | 脚本放在**外置盘**（`/Volumes/...`）上。外置卷受 **TCC 保护**，launchd 拉起的 `/bin/bash` 没有完全磁盘访问权限，读不到脚本 | 把脚本拷到**内置盘**（如 `~/.local/bin/`）再跑。**别给 `/bin/bash` 授 FDA**——等于给所有脚本开后门。副作用是好的：运行时不再依赖外置盘挂载 |
| **L3** | 定时任务里调 `npm`/`node`（fnm/nvm 管理的）找不到命令 | `which npm` 解析到 `~/.local/state/fnm_multishells/<PID>_<ts>/bin/npm`——**路径带 PID，每个 shell 不同**，launchd 里必然失效 | 别在定时脚本里调这些包装器。要清缓存直接 `rm -rf ~/.npm/_cacache`（会自建）。要调 CLI 用绝对路径兜底 |
| **L4** | 定时任务里依赖 `orb`/`code`/`brew` 等，静默跳过或失败，终端里却能跑 | launchd 的 PATH 极简，**不含 `/usr/local/bin`**（很多 CLI 装那） | 脚本里显式找绝对路径（逐个试 `/usr/local/bin/X`、`/opt/homebrew/bin/X`）；plist 的 `EnvironmentVariables.PATH` 也补 `/usr/local/bin` |
| **L5** | plist 里写 `~/.local/bin/x.sh` 或 `$HOME/...` 不生效 | **plist 不做 `~` / `$HOME` 展开**，必须绝对路径 | 模板里用 `__HOME__` 占位符，install 脚本 `sed` 换成真实家目录 |
| **L6** | 定时任务静默烂掉，几个月后才发现没跑 | 没有失败告知机制 | `trap ... EXIT` 捕获非零退出并推送通知；`launchctl print gui/$UID/<label> \| grep "last exit"` 查上次退出码 |
| **L7** | install 脚本报 `LABEL�: unbound variable` 之类 | shell 变量名后**紧跟中文全角字符**，bash 把多字节字节吞进变量名 | 用 `${LABEL}` 显式界定边界 |

## 迁移 / 删除

| # | 症状 | 根因 | 解法 |
|---|------|------|------|
| **M1** | 启用外置盘 owners 后整盘数据变得不可读 | 盘原本 `Owners: Disabled`，已有数据在忽略所有权下写入、uid 未经校验；`enableOwnership` 后这些 uid 突然生效 | **不要** `enableOwnership`。保持 Disabled，只迁不依赖权限位的数据（App 数据、归档），不迁 `~/.ssh`/`~/.gnupg`/`.m2` 这类靠 0600/0700 的目录 |
| **M2** | 迁移微信/沙盒 App 后启动异常、聊天记录被重建 | 软链了**容器根目录**。根目录有 `.com.apple.containermanagerd.metadata.plist`，`containermanagerd` 会校验容器结构与所有权，根被换成软链 → 拒绝启动或重建容器 | 只软链**内层** `Data/Documents`（大头通常都在这），不动容器根。动手前 `cp -Rp` 备份，验证聊天记录完整 |
| **M3** | App 更新/重启后软链「失效」，数据又长回内置盘 | 软链设在了应用会 `rename`/删除重建的那一层（如某个 bundle 目录） | 软链设在**更外层的稳定目录**：应用在其内部创建/重建子目录时，落到软链目标（外置盘），软链本身不受影响。判断方法见 migration.md |
| **M4** | 删掉的孤儿镜像过几天又出现，mtime 还是几个月前 | APFS `clonefile` 重新克隆，保留原始元数据 → mtime 看起来「从没删过」 | 接受它会重生，纳入定期清理；清前用 `lsof` + 数据路径配置双重确认它确是孤儿而非活跃镜像 |
| **M5** | 用 `du` 大小相等判断迁移成功，其实文件有差异/或误判丢失 | `du` 是**磁盘占用**（分配块），跨文件系统本就不同（APFS 簇分配、`.DS_Store`）；反之逻辑一致时 du 也可能不等 | 用 `rsync -an --checksum --itemize-changes` 逐文件校验和比对（无输出=一致）+ `find -type f \| wc -l` 比文件数 |
| **M6** | 跨盘 `mv` 中断后源文件损坏/丢失 | 跨卷 `mv` 是 copy+unlink，中途中断留下半个文件 | 用 `rsync -a`（或 `--remove-source-files`）：先完整复制、校验通过、再删源。删源前务必确认备份可用 |
| **M7** | 迁移后重启，App 读到空目录 | 外置盘在**登录过程中**才挂载，App 可能抢在挂载完成前启动 | 迁移后必须**重启验证一次**；出现竞态的软链项回滚。用 `readlink` 自检软链存活 |

## 判断类

| # | 场景 | 要点 |
|---|------|------|
| **J1** | 判断一个大镜像/文件是死是活 | 看 `atime`（`stat -f "%Sa"`，最后读取时间）和 `lsof <file>`（谁打开着），别只看 `du` 大小或 mtime |
| **J2** | 稀疏文件迷惑 | VM 镜像逻辑大小可能是 TB 级（`stat -f%z`），实占才几 G（`du -h`）。看实占判断收益 |
| **J3** | 搞清占空间的到底是什么 | 例：LM Studio 占空间常是 `extensions/backends`（推理引擎）而非 `models`（模型可能是 0B）。对症才能选对处理方式 |
