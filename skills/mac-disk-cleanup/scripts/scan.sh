#!/bin/bash
#
# 磁盘占用全面扫描（只读，不改任何东西）。
# 输出分层占用清单，供 Step 2 分类使用。
#
#   用法: scan.sh            扫描家目录 + Library + 隐藏目录 + 外置盘概况
#         scan.sh --deep     额外深入 Application Support / Containers 子目录
#
set -euo pipefail

hr() { printf '\n== %s ==\n' "$1"; }

hr "磁盘可用（Data 卷才是真正会满的）"
df -h /System/Volumes/Data | awk 'NR==1 || /Data/{print}'

hr "家目录顶层 top 20"
du -sh -x "$HOME"/* 2>/dev/null | sort -rh | head -20

hr "隐藏目录 top 15（开发工具链/缓存常在此）"
du -sh "$HOME"/.[a-z]* 2>/dev/null | sort -rh | head -15

hr "~/Library 各区 top"
du -sh -x "$HOME/Library"/* 2>/dev/null | sort -rh | head -10

hr "Application Support top 10"
du -sh -x "$HOME/Library/Application Support"/* 2>/dev/null | sort -rh | head -10

hr "Containers top 8（沙盒 App，注意内层 Data/Documents）"
du -sh -x "$HOME/Library/Containers"/* 2>/dev/null | sort -rh | head -8

hr "Group Containers top 6（易藏迁移后的孤儿镜像）"
du -sh -x "$HOME/Library/Group Containers"/* 2>/dev/null | sort -rh | head -6

hr "Caches top 10"
du -sh -x "$HOME/Library/Caches"/* 2>/dev/null | sort -rh | head -10

hr "外置盘概况（判断能否/如何迁移）"
# 列出所有 /Volumes 下的挂载点及其文件系统、owners 状态
for v in /Volumes/*; do
    [ -d "$v" ] || continue
    info=$(diskutil info "$v" 2>/dev/null) || continue
    fs=$(printf '%s' "$info"  | awk -F': *' '/File System Personality/{print $2}')
    own=$(printf '%s' "$info" | awk -F': *' '/Owners/{print $2}')
    avail=$(df -h "$v" 2>/dev/null | awk 'NR==2{print $4}')
    printf '  %-28s  fs=%-6s  owners=%-9s  avail=%s\n' "$v" "${fs:-?}" "${own:-?}" "${avail:-?}"
done

if [ "${1:-}" = "--deep" ]; then
    hr "本地快照（占空间但系统管辖，勿手删；可 thinlocalsnapshots 回收）"
    tmutil listlocalsnapshots / 2>/dev/null | head
    hr "疑似大镜像文件（判断死/活见 classification.md 的三信号）"
    find "$HOME/Library" -type f \( -name "*.img" -o -name "*.raw" -o -name "*.qcow2" \) 2>/dev/null \
        | while read -r f; do printf '  %s  实占 %s  atime %s\n' "$f" "$(du -h "$f" | cut -f1)" "$(stat -f '%Sa' -t '%Y-%m-%d' "$f")"; done
fi

printf '\n扫描完成。接下来：把上面的大头按四类归档（可重建缓存 / 死数据孤儿 / 可迁移App数据 / 纯归档），见 SKILL.md Step 2。\n'
