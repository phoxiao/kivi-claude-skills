#!/bin/bash
#
# 可重建缓存 / 死数据孤儿的定时清理脚本（模板）。
# 由 launchd 每日调用，仅当可用空间低于阈值才真正动手——平时零打扰、零 IO，不白扔热缓存。
#
#   cleanup-caches.sh            正常运行（低于阈值才清理）
#   cleanup-caches.sh --dry-run  只报告会删什么，不删
#   cleanup-caches.sh --force    忽略阈值，立即清理
#
# 适配到你的机器：
#   - 调 THRESHOLD_GB。
#   - clean_* 函数里的路径按 scan.sh 扫出来的大头增删；只放「可重建 / 已验证的孤儿」。
#   - OrbStack 孤儿清理默认开启，仅在 data_dir 指向外置盘时才删（见守卫）；不用可删掉该函数调用。
#   - notify() 默认用 macOS 本地通知；想推手机把它换成 curl 你的 webhook。
#
# 设计约束（改前必读）：
#   1. 不调 npm/node 等 fnm/nvm 包装器——它们的路径带 shell PID，launchd 里必失效（pitfalls L3）。
#      清缓存直接删目录，工具会自建。
#   2. 所有删除必须走 safe_rm()：强制路径非空、在 $HOME 下、深度 >=2、不含 ..。
#      定时任务里 `rm -rf $VAR` 一旦 VAR 为空就是灾难，这个守卫是硬性要求。
#   3. 只删可重建的缓存和已验证的孤儿。不可恢复的数据不属于这里。
#
set -euo pipefail

# ---- 配置 ----
THRESHOLD_GB=30                                   # 可用低于此值(GB)才触发清理
LOG_FILE="$HOME/Library/Logs/disk-cleanup.log"

DRY_RUN=0; FORCE=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --force)   FORCE=1 ;;
        *) echo "未知参数: $arg" >&2; exit 2 ;;
    esac
done

mkdir -p "$(dirname "$LOG_FILE")"
log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"; }

# Data 卷才是真正会满的那个
free_gb() { df -k /System/Volumes/Data | awk 'NR==2 {printf "%d", $4/1024/1024}'; }

# 默认用 macOS 本地通知。想推手机：把这里换成 curl 你的 webhook（如 Bark: curl -s "https://api.day.app/<key>?title=..&body=..")
notify() {
    local title="$1" body="$2"
    osascript -e "display notification \"$body\" with title \"$title\"" 2>>"$LOG_FILE" || log "通知失败(不影响清理)"
}

# 删除守卫：拒绝空路径、$HOME 外、$HOME 下不足两层、含 .. 的路径
safe_rm() {
    local target="${1:-}"
    [ -n "$target" ] || { log "  !! 拒绝：空路径"; return 1; }
    case "$target" in
        "$HOME"/*/*) ;;
        *) log "  !! 拒绝（不在 \$HOME 下或层级过浅）：$target"; return 1 ;;
    esac
    case "$target" in *..*) log "  !! 拒绝（含 ..）：$target"; return 1 ;; esac
    [ -e "$target" ] || { log "  -  跳过（不存在）：${target#$HOME/}"; return 0; }
    local size; size=$(du -sh "$target" 2>/dev/null | cut -f1 || echo "?")
    if [ "$DRY_RUN" -eq 1 ]; then log "  [dry-run] 会删除：${target#$HOME/}  ($size)"; return 0; fi
    rm -rf -- "$target"
    log "  ✓  已删除：${target#$HOME/}  ($size)"
}

# 进程在跑就别动它的缓存
is_running() { pgrep -qf "$1" 2>/dev/null; }

# ---- 清理项（按 scan.sh 扫出的大头增删）----

clean_package_managers() {
    log "[包管理器缓存]"
    safe_rm "$HOME/.npm/_cacache"                    # npm 自建
    safe_rm "$HOME/.npm/_npx"                        # npx 临时安装，不受 npm cache clean 管辖
    safe_rm "$HOME/.cache/uv"                        # uv 自建
    safe_rm "$HOME/Library/Caches/Homebrew"          # brew bottle 残留
}

clean_ai_tools() {
    log "[AI 工具缓存]"
    if is_running "[Cc]odex"; then log "  -  跳过 codex 缓存（进程运行中）"
    else
        safe_rm "$HOME/.cache/codex-runtimes"
        safe_rm "$HOME/Library/Caches/com.openai.codex"
    fi
}

clean_updater_leftovers() {
    log "[更新器残留包]"
    # *-updater / *.ShipIt 是 Electron 应用下载完忘了删的安装包。glob 泛化，新应用自动覆盖。
    # 正在更新的 App 别删其 ShipIt——用 is_running 守卫（这里以 Claude 为例，按需增删）。
    local hit
    for hit in "$HOME"/Library/Caches/*-updater "$HOME"/Library/Caches/*.ShipIt; do
        [ -e "$hit" ] || continue
        case "$hit" in
            *claudefordesktop.ShipIt)
                is_running "Claude.app/Contents/MacOS/Claude" \
                    && { log "  -  跳过 Claude ShipIt（Claude 运行中，可能正在更新）"; continue; } ;;
        esac
        safe_rm "$hit"
    done
    safe_rm "$HOME/Library/Caches/electron"
}

clean_build_caches() {
    log "[编译缓存]"
    safe_rm "$HOME/Library/Caches/go-build"          # Go 编译缓存，自建（不调 go clean，launchd 里未必有 go）
}

# OrbStack 迁 data_dir 到外置盘后 group container 里的孤儿镜像（会被 clonefile 重生，pitfalls M4）。
# 三重守卫（缺一不删）：orb 用绝对路径找(pitfalls L4) + data_dir 指外置盘 + 目标未被 lsof 打开。
clean_orbstack_orphan() {
    log "[OrbStack 死镜像]"
    local orphan="$HOME/Library/Group Containers/HUAQ24HBR6.dev.orbstack/data/data.img.raw"
    [ -e "$orphan" ] || { log "  -  跳过（不存在）"; return 0; }
    local orb=""
    for c in /usr/local/bin/orb /opt/homebrew/bin/orb; do [ -x "$c" ] && { orb="$c"; break; }; done
    [ -n "$orb" ] || { log "  !! 跳过：找不到 orb，无法确认 data_dir，不敢删"; return 0; }
    local ddir; ddir=$("$orb" config get data_dir 2>/dev/null) || true
    case "$ddir" in
        /Volumes/*) ;;
        *) log "  !! 跳过：data_dir='$ddir' 未指向外置盘，可能是活跃数据"; return 0 ;;
    esac
    if lsof -- "$orphan" >/dev/null 2>&1; then log "  !! 跳过：镜像正被打开（非孤儿）"; return 0; fi
    safe_rm "$orphan"
}

# 注：故意不清 ms-playwright / .cache/puppeteer / Library/Caches/Google（重下浏览器二进制代价高 / 拖慢浏览）。

# ---- 主流程 ----
main() {
    local before after reclaimed
    before=$(free_gb)
    log "──────── 检查开始（可用 ${before}G / 阈值 ${THRESHOLD_GB}G）────────"

    if [ "$FORCE" -eq 0 ] && [ "$DRY_RUN" -eq 0 ] && [ "$before" -ge "$THRESHOLD_GB" ]; then
        log "空间充足，无需清理。"; exit 0
    fi
    [ "$FORCE" -eq 1 ] && log "（--force：忽略阈值）"
    [ "$DRY_RUN" -eq 1 ] && log "（--dry-run：不会真的删除）"

    clean_package_managers
    clean_ai_tools
    clean_updater_leftovers
    clean_build_caches
    clean_orbstack_orphan

    if [ "$DRY_RUN" -eq 1 ]; then log "──────── dry-run 结束 ────────"; exit 0; fi

    after=$(free_gb); reclaimed=$(( after - before ))
    log "──────── 完成：释放 ${reclaimed}G，当前可用 ${after}G ────────"
    if [ "$after" -lt "$THRESHOLD_GB" ]; then
        notify "⚠️ 磁盘清理：空间仍紧张" "释放 ${reclaimed}G 后仍只剩 ${after}G。缓存已清干净，需手工处理大文件。"
    else
        notify "🧹 磁盘清理完成" "释放 ${reclaimed}G，当前可用 ${after}G。"
    fi
}

# 未捕获的失败要让你知道，否则定时任务静默烂掉（pitfalls L6）
trap 'rc=$?; [ $rc -ne 0 ] && { log "!! 脚本异常退出 (exit $rc)"; notify "❌ 磁盘清理失败" "脚本 exit $rc，详见 $LOG_FILE"; }' EXIT

main
