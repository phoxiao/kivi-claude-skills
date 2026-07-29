# Step 2 分类判断技巧

把扫描到的大头准确归类，是整个流程的关键——归错类会导致删错或白删。

## 四类的判别问题

对每个大头，依次问：

1. **删了会自动重建吗？** → 是 → **可重建缓存**。特征：目录名含 `cache`/`Cache`/`_cacache`、`*-updater`、`*.ShipIt`、`build`、`runtimes`；或位于 `~/Library/Caches`、`~/.cache`、`~/.npm`。删除代价只是「下次慢一点」。

2. **曾经有用但现在没进程碰吗？** → 是 → **死数据孤儿**。特征：`atime` 很旧（半年没读）、`lsof` 查不到打开者、应用的数据路径已改到别处。常见于：迁移数据目录后的旧副本、卸载残留、旧版本 VM 镜像。

3. **应用当前在用、不能删，但能挪位置吗？** → 是 → **可迁移 App 数据**。特征：`lsof` 显示被活跃进程打开、mtime 是最近、删了 App 会丢数据或崩溃。如 Electron 应用的大数据目录、本地 VM/容器镜像、大模型文件、聊天记录容器。

4. **是用户自己的文件、本就该放大盘吗？** → 是 → **纯归档**。如 Downloads 里的旧文档、电子书、课程视频、照片。

## 关键判断：活跃镜像 vs 死孤儿

大镜像文件（`.img`/`.raw`/`.qcow2`/`.vmdk`）最容易误判，因为它们又大又「像系统文件」。用三个信号交叉验证：

```bash
F="/path/to/some.img.raw"
stat -f "逻辑 %z 字节 | mtime %Sm | atime %Sa" -t "%Y-%m-%d %H:%M" "$F"
du -h "$F"                  # 实占（稀疏文件逻辑≠实占）
lsof -- "$F" 2>/dev/null    # 有输出=某进程正打开=活跃，绝不能删
```

- **活跃**：`lsof` 有打开者，或 mtime/atime 是最近 → 归「可迁移 App 数据」，迁移不删除。
- **孤儿**：`lsof` 空、atime 很旧、且应用配置已指向别处 → 归「死数据孤儿」，验证后删。

典型案例：OrbStack 把 `data_dir` 改到外置盘后，`~/Library/Group Containers/HUAQ24HBR6.dev.orbstack/data/data.img.raw` 成为孤儿——`orb config get data_dir` 指向外置盘、`lsof` 显示 OrbStack 打开的是外置盘那个、内置这个 atime 停在几个月前。这就是可删的死孤儿（但会被 clonefile 重生，见 pitfalls M4）。

## 缓存里的例外：别一刀切

不是所有 `Caches` 都该无脑清。删除代价高的要**手动保留**：
- `ms-playwright`、`~/.cache/puppeteer` —— 删了要重下浏览器二进制，国内网络代价过高；
- 浏览器自身缓存（`Library/Caches/Google` 等）—— 重建会拖慢日常浏览体验。

这些从定时清理里排除，只在空间极度告急时手工处理。

## 沙盒容器：看内层分布再决定

微信、企业微信这类沙盒 App 的容器（`~/Library/Containers/<bundle-id>`）属「可迁移 App 数据」，但**迁移前先看内层大小分布**：

```bash
du -sh ~/Library/Containers/<bundle-id>/Data/* 2>/dev/null | sort -rh | head
```

通常大头集中在 `Data/Documents`（聊天记录、文件）。只软链这一层即可拿到几乎全部收益，且风险远低于软链容器根（见 pitfalls M2）。`Data/Library` 含运行状态，不建议动。
