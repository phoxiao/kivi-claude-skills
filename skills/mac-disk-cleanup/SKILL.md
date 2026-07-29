---
name: mac-disk-cleanup
description: >-
  Mac 磁盘空间梳理与优化的系统方法论——扫描占用、分类分诊、分级处理、迁移到外置盘、
  搭建定时清理。核心是「分诊而非乱删」：先看全貌再动手，删除前验证、迁移前校验和比对。
  Use this skill WHENEVER the user mentions 磁盘满/内置盘空间不足/清理空间/腾空间/
  优化存储/迁移到外置盘/disk full/low disk space/free up storage/storage optimization,
  or asks why the disk is full, or wants to move app data / caches / downloads off the
  internal SSD, or wants a recurring cleanup job. Trigger even if they just say
  "我的 Mac 快满了" without naming a specific fix — this skill IS the diagnostic method.
  macOS only (uses APFS / launchd / TCC specifics).
---

# /mac-disk-cleanup — Mac 磁盘空间梳理与优化

## 核心原则：分诊，不是乱删

看到一个大目录就删，是新手做法，会踩两种坑：**删错**（清掉了不可恢复的数据）或**白删**（清掉的缓存几天就长回来）。正确的做法像急诊分诊——先看全貌，把占用**分类**，再按「风险 × 收益」排序处理。

这个 skill 的价值不在于替用户按删除键，而在于把一次盲目的清理，升级为一套**可复现、可验证、可自动化**的流程。关键决策（哪些迁、盘拔不拔、聊天记录要不要动）永远交给用户拍板——因为只有用户知道数据对自己的价值。

四步工作流：**扫描 → 分类 → 分级处理 → 验证/自动化**。

---

## Step 1：全面扫描（只读）

先建立全貌，不要一上来就盯着某个目录。用 `scripts/scan.sh` 一次性产出分层占用清单，或手动跑核心命令：

```bash
# 真正会满的是 Data 卷，不是笼统的 /
df -h /System/Volumes/Data

# 家目录、隐藏目录、Library 三个维度的大头
du -sh -x ~/* 2>/dev/null | sort -rh | head -20
du -sh ~/.[a-z]* 2>/dev/null | sort -rh | head -15
du -sh -x ~/Library/{Application\ Support,Containers,Group\ Containers,Caches}/* 2>/dev/null | sort -rh | head -20
```

扫描时**同时留意外置盘**（`df -h`）——它是不是 APFS、常年连接还是移动使用、`Owners` 是否启用。这些直接决定 Step 3 能用哪种迁移方式。

关键陷阱：`du` 报的是**磁盘占用**（分配的块），不是逻辑字节。稀疏文件（如 VM 镜像 `data.img.raw` 逻辑 8TB、实占 9G）会让人误判。判断一个大镜像是否活跃，看 `atime`（最后读取）和 `lsof`（谁打开着），别只看 `du`。

---

## Step 2：分类（分诊的核心）

把扫出来的大头归入四类——**类别决定处理方式和风险**：

| 类别 | 判别特征 | 例子 | 处理方向 |
|---|---|---|---|
| **可重建缓存** | 删了会自动重新生成，只是慢一点 | `~/.npm/_cacache`、`go-build`、`*-updater`、`codex-runtimes` | 删（治标）→ 纳入定时清理（治本） |
| **死数据孤儿** | 曾经有用、现在没进程碰、会因某种机制重生 | OrbStack 迁移后遗留的旧镜像、卸载残留 | 验证确是孤儿后删；若会重生则纳入定时清理 |
| **可迁移 App 数据** | 应用当前在用、不能删、但可挪位置 | Claude vm_bundles、微信/企业微信容器、大模型文件 | 迁移（软链 / 官方设置改路径） |
| **纯归档** | 用户文件、本就该长在大盘上 | Downloads 里的旧文档、Books、课程 | 直接移动到外置盘，不软链 |

分类时的判断技巧见 `references/classification.md`（如何区分「活跃镜像」vs「死孤儿」、缓存 vs 数据）。

---

## Step 3：分级处理（风险从低到高）

**永远按风险递增的顺序做**，每步之后 `df -h /System/Volumes/Data` 确认。任何一步都能独立停下。

### 3a. 可重建缓存 —— 零风险删除

最安全，先做。但**删除必须走守卫**，绝不裸奔 `rm -rf $VAR`（变量为空就是灾难）。用 `scripts/cleanup-caches.sh` 里的 `safe_rm()` 模式：强制路径非空、位于 `$HOME` 下、深度 ≥2 层、不含 `..`。

进程在跑就跳过它的缓存（`is_running` 守卫），否则可能删坏正在使用的文件。

### 3b. 死数据孤儿 —— 验证后删除

删之前必须**证明它确实是孤儿**，否则可能误删活跃数据。三重确认（以 OrbStack 迁移后的遗留镜像为例）：
1. 应用的数据路径已改到别处（`orb config get data_dir` 指向外置盘）；
2. `lsof` 确认目标文件没被任何进程打开；
3. `atime` 显示它很久没被读过。

注意：有些孤儿删了会**重生**（APFS `clonefile` 克隆回来，还保留原始 mtime，看起来像没删过）——这种别指望删一次了事，纳入定时清理。

### 3c. 可迁移 App 数据 —— 三种迁移方式，优先级从高到低

**方式一：官方设置改数据路径（最干净，零软链风险）**
先查应用有没有自带的「数据目录」设置（如 OrbStack 的 `data_dir`、LM Studio 的模型目录）。有就用它——应用自己管理路径，不依赖软链。
> 陷阱：先搞清占空间的到底是什么。例如 LM Studio 占空间的常是**后端引擎**（`extensions/backends`）而非模型，官方「模型目录」设置迁不动引擎——那种情况要么软链要么卸载。

**方式二：软链迁移（App 活跃数据，需外置盘常年连接）**
```bash
# 先完全退出 App，再动它的数据
mv ~/Library/.../TARGET  /Volumes/EXTERNAL/Offloaded/TARGET
ln -s /Volumes/EXTERNAL/Offloaded/TARGET  ~/Library/.../TARGET
```
关键决策见 `references/migration.md`：**软链设在哪一层**（设外层目录，别设应用可能会 rename/重建的内层 bundle）、**沙盒容器只软链内层 `Data/Documents`**（不能软链容器根，`containermanagerd` 会校验并重建 → 聊天记录丢失）、**退出 App 再动数据**。

**方式三：直接移动（纯归档，最安全）**
纯用户文件直接 `mv` 到外置盘，**不软链**——软链只会掩盖真实位置。但跨盘移动要 `copy → 校验 → 删源`，别用裸 `mv`（跨盘 mv 中断会留下半个文件）。见 3d 的验证。

### owners 红线（外置盘）
如果外置盘 `Owners: Disabled`，**不要**为了迁移而 `diskutil enableOwnership`——盘上已有数据是在忽略所有权状态下写入的，启用后记录的 uid 突然生效**可能导致整盘不可读**。代价是：不迁依赖权限位的目录（`~/.ssh`、`~/.gnupg` 等），单用户环境下这些本就不需要迁。

---

## Step 4：验证与自动化

### 迁移前验证（copy → verify → delete，绝不 mv 了事）
```bash
rsync -a "$SRC" "$DST/"                                  # 只增不删
rsync -an --checksum --itemize-changes "$SRC" "$DST/"    # 金标准：无输出=逐文件校验和一致
# 文件数也比一遍，确认无误后才删源
```
不要用 `du` 大小相等来判断迁移成功——跨文件系统 `du`（磁盘占用）本就会差，`--checksum` 的逐文件比对才是真相。

### 迁移后（软链项）
- `readlink <path>` 自检软链是否还在、指向对不对；
- **重启一次**再验证：外置盘在登录过程中才挂载，App 可能抢在挂载完成前启动、读到空目录（竞态）。发现此类问题的软链项需回滚。

### 治本：定时清理
缓存和会重生的孤儿，手动删是治标。用 `scripts/cleanup-caches.sh` + `scripts/install-cron.sh` 搭一个 launchd 定时任务：**每天检查、低于阈值才清**（平时零打扰、零 IO，不白扔热缓存）。部署有若干 macOS 特有的坑（launchd 拒软链 plist、外置卷 TCC 阻断、fnm 临时路径、launchd PATH 精简），**照做前务必读 `references/pitfalls.md`**，这些坑每一个都会让定时任务静默失败。

---

## 配套资源

**脚本（`scripts/`，都是经实战验证的模板，用前按注释适配路径/阈值）：**
- `scan.sh` — 全面只读扫描，输出分类占用清单
- `cleanup-caches.sh` — 定时清理主脚本：`safe_rm` 守卫 + 进程守卫 + glob 泛化更新器残留 + OrbStack 孤儿三重守卫
- `install-cron.sh` + `disk-cleanup.plist.tmpl` — 一键部署 launchd 定时任务（拷贝而非软链，规避两个部署坑）

**参考（`references/`，按需读取）：**
- `pitfalls.md` — **踩坑速查表**（部署定时任务、迁移前必读）
- `classification.md` — Step 2 分类判断技巧
- `migration.md` — Step 3c 迁移的关键决策（软链层级、沙盒容器、owners）

## 沟通基调
这是会改动用户系统的操作。删除不可逆、迁移影响 App。始终：先呈现分类清单和分级方案让用户看清，风险高的项（沙盒容器、App 数据）先备份再动手，需要用户拍板的（盘拔不拔、数据价值）用提问而非替他决定。报告结果如实——释放了多少、当前剩多少、哪步跳过了。
