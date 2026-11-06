#!/bin/bash
#
# 执行卸载：按正确顺序清掉一个 macOS 应用的本体、数据和开机代理。
#
#   用法:
#     uninstall-app.sh "Discord"              先看会删什么（默认就是预演，不会删）
#     uninstall-app.sh "Discord" --execute    真删
#     uninstall-app.sh --id com.hnc.Discord --execute
#
# 为什么默认预演：卸载不可逆，应用的授权文件、许可证、本地配置都在数据目录里。
# 让「看清单」和「按下删除」分成两次动作，是为了给判断留出位置。
#
# ── 顺序为什么是这个顺序（踩过才知道）──────────────────────────────────
#
# 1. 先卸载并删除 LaunchAgent/LaunchDaemon
# 2. 再优雅退出应用
# 3. 再终止残留进程
# 4. 然后删 .app 本体
# 5. 最后删数据目录
#
# 顺序反了会怎样：Ardot（腾讯 CoCraft）的 LaunchAgent 写着 KeepAlive=true，
# 先 pkill 的话 launchd 立刻重新拉起来，PID 变了但进程还在，看起来像杀不死。
# 必须先把 plist bootout 掉并删除，守护没了进程才杀得干净。
#
# 反过来，如果只删 .app 不删 plist，launchd 会一直去拉一个不存在的程序，
# 每次开机都失败重试——这是"卸载了但没卸干净"最常见的形态。

set -uo pipefail

RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
[ -t 1 ] || { RED=""; GRN=""; YEL=""; DIM=""; BOLD=""; OFF=""; }

EXECUTE=0; TARGET=""; BY_ID=0
while [ $# -gt 0 ]; do
    case "$1" in
        --execute) EXECUTE=1 ;;
        --id)      BY_ID=1; shift; TARGET="${1:-}" ;;
        -*)        echo "未知参数: $1" >&2; exit 2 ;;
        *)         TARGET="$1" ;;
    esac
    shift
done
[ -n "$TARGET" ] || { echo "用法: $0 <App名 | --id <bundle-id>> [--execute]" >&2; exit 2; }

say() { echo "$@"; }
act() { # act <描述> <路径>  —— 预演时只打印，执行时才动手
    local desc="$1" path="$2"
    if [ "$EXECUTE" = 0 ]; then
        printf "  ${DIM}[预演]${OFF} %s  %s (%s)\n" "$desc" "${path/#$HOME/~}" "$(du -sh "$path" 2>/dev/null | cut -f1)"
    else
        rm -rf -- "$path" && printf "  ${GRN}✓${OFF} %s  %s\n" "$desc" "${path/#$HOME/~}"
    fi
}

# ---- 定位 -----------------------------------------------------------------

if [ "$BY_ID" = 0 ]; then
    APP=""
    for cand in "$TARGET" "/Applications/$TARGET.app" "$HOME/Applications/$TARGET.app"; do
        [ -d "$cand" ] && [[ "$cand" == *.app ]] && { APP="$cand"; break; }
    done
    [ -n "$APP" ] || APP=$(mdfind "kMDItemContentType == 'com.apple.application-bundle' && kMDItemFSName == '$TARGET.app'" 2>/dev/null | head -1)
    [ -n "$APP" ] || { echo "${RED}找不到应用 '$TARGET'${OFF}" >&2; exit 1; }
    BID=$(plutil -extract CFBundleIdentifier raw "$APP/Contents/Info.plist" 2>/dev/null)
    DISP=$(basename "$APP" .app)
else
    BID="$TARGET"
    APP=$(mdfind "kMDItemCFBundleIdentifier == '$BID'" 2>/dev/null | grep '\.app$' | head -1)
    DISP=$([ -n "$APP" ] && basename "$APP" .app)
fi
DISP="${DISP:-}"

# ---- 拒绝清单（这些不该走这个脚本）------------------------------------------

case "${APP:-}" in
    /System/*|/Applications/Utilities/*)
        echo "${RED}拒绝：系统应用不能用本脚本卸载${OFF}" >&2; exit 1 ;;
    /Applications/Setapp/*)
        echo "${RED}拒绝：Setapp 托管的应用必须在 Setapp 客户端里卸载。"
        echo "直接删会被 Setapp 自动装回，白忙一场。${OFF}" >&2; exit 1 ;;
esac
if [ -n "${APP:-}" ] && [ -d "$APP" ] && [ "$(stat -f '%Su' "$APP")" != "$(id -un)" ]; then
    echo "${YEL}注意：$APP 属主是 $(stat -f '%Su' "$APP")，删除需要 sudo。"
    echo "本脚本不会替你 sudo——请自行确认后手动执行。${OFF}"
fi

# ---- 归属判定（与 audit-app.sh 保持一致，改一处要同步改另一处）--------------

belongs() {
    local n="$1" base="${1%.*}" lastseg lowdisp
    if [ -n "$BID" ]; then
        [ "$n" = "$BID" ] && return 0
        [ "$base" = "$BID" ] && return 0
        case "$n" in "$BID".*) return 0 ;; esac
        case "$n" in *."$BID") return 0 ;; esac
        case "$base" in *."$BID") return 0 ;; esac
    fi
    if [ -n "$DISP" ] && [ ${#DISP} -ge 4 ]; then
        [ "$n" = "$DISP" ] && return 0
        [ "$base" = "$DISP" ] && return 0
        case "$n" in "$DISP".*|"$DISP"-*) return 0 ;; esac
        lowdisp=$(printf '%s' "$DISP" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
        lastseg=$(printf '%s' "$n" | tr '[:upper:]' '[:lower:]' | awk -F. '{print $NF}')
        [ "$lastseg" = "$lowdisp" ] && return 0
    fi
    return 1
}

echo "${BOLD}卸载 ${DISP:-$BID}${OFF}  (bundle id: ${BID:-未知})"
[ "$EXECUTE" = 0 ] && echo "${YEL}预演模式 —— 什么都不会删。确认无误后加 --execute。${OFF}"
echo

# ---- 第 1 步：开机代理（必须最先，否则进程杀不死）--------------------------

echo "${BOLD}[1/5] 开机代理${OFF}"
AGENTS=0
for d in "$HOME/Library/LaunchAgents"; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
        [ -e "$f" ] || continue
        belongs "$(basename "$f")" || continue
        AGENTS=1
        label=$(basename "$f" .plist)
        if [ "$EXECUTE" = 1 ]; then
            launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$f" 2>/dev/null
        fi
        act "卸载并删除代理" "$f"
    done
done
# /Library 下的需要 sudo，本脚本只报告不动手
for d in /Library/LaunchAgents /Library/LaunchDaemons /Library/PrivilegedHelperTools; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
        [ -e "$f" ] || continue
        belongs "$(basename "$f")" || continue
        AGENTS=1
        echo "  ${YEL}需 sudo，请手动处理：sudo rm -rf '$f'${OFF}"
    done
done
[ "$AGENTS" = 0 ] && echo "  ${DIM}(无)${OFF}"

# ---- 第 2、3 步：退出应用 ---------------------------------------------------

echo "${BOLD}[2/5] 退出应用${OFF}"
if [ -n "${APP:-}" ] && pgrep -qf "$APP" 2>/dev/null; then
    if [ "$EXECUTE" = 1 ]; then
        [ -n "$DISP" ] && osascript -e "tell application \"$DISP\" to quit" 2>/dev/null
        for _ in 1 2 3 4 5 6 7 8; do pgrep -qf "$APP" 2>/dev/null || break; sleep 1; done
        if pgrep -qf "$APP" 2>/dev/null; then
            echo "  ${DIM}优雅退出无效，强制终止${OFF}"
            pkill -f "$APP" 2>/dev/null; sleep 2
        fi
        pgrep -qf "$APP" 2>/dev/null \
            && echo "  ${RED}仍有进程存活 —— 检查是否还有没清掉的守护${OFF}" \
            || echo "  ${GRN}✓${OFF} 已退出"
    else
        echo "  ${DIM}[预演]${OFF} 会退出 $(pgrep -cf "$APP" 2>/dev/null) 个进程"
    fi
else
    echo "  ${DIM}(未在运行)${OFF}"
fi

# ---- 第 4 步：App 本体 ------------------------------------------------------

echo "${BOLD}[3/5] 应用本体${OFF}"
if [ -n "${APP:-}" ] && [ -d "$APP" ]; then
    case "$APP" in
        /Applications/*.app|"$HOME"/Applications/*.app) act "删除" "$APP" ;;
        *) echo "  ${RED}拒绝：路径不在 /Applications 或 ~/Applications 下：$APP${OFF}" ;;
    esac
else
    echo "  ${DIM}(.app 已不存在)${OFF}"
fi

# ---- 第 5 步：数据残留 ------------------------------------------------------

echo "${BOLD}[4/5] 数据残留${OFF}"
DATA=0
for base in \
    "$HOME/Library/Application Support" \
    "$HOME/Library/Containers" \
    "$HOME/Library/Group Containers" \
    "$HOME/Library/Caches" \
    "$HOME/Library/Preferences" \
    "$HOME/Library/Preferences/ByHost" \
    "$HOME/Library/Saved Application State" \
    "$HOME/Library/HTTPStorages" \
    "$HOME/Library/WebKit" \
    "$HOME/Library/Logs" \
    "$HOME/Library/Application Scripts" ; do
    [ -d "$base" ] || continue
    for f in "$base"/*; do
        [ -e "$f" ] || continue
        belongs "$(basename "$f")" || continue
        case "$f" in "$HOME"/Library/*/*) ;; *) echo "  ${RED}拒绝（路径异常）：$f${OFF}"; continue ;; esac
        DATA=1
        act "删除" "$f"
    done
done
if [ -n "$DISP" ] && [ ${#DISP} -ge 4 ]; then
    lower=$(printf '%s' "$DISP" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
    for f in "$HOME/.$lower" "$HOME/.config/$lower"; do
        [ -e "$f" ] || continue
        case "$f" in "$HOME"/.?*) ;; *) continue ;; esac
        DATA=1
        act "删除（家目录隐藏）" "$f"
    done
fi
[ "$DATA" = 0 ] && echo "  ${DIM}(无)${OFF}"

# ---- 复查 ------------------------------------------------------------------

echo "${BOLD}[5/5] 复查${OFF}"
if [ "$EXECUTE" = 0 ]; then
    echo "  ${DIM}预演模式跳过。确认上面清单无误后重跑并加 --execute。${OFF}"
    exit 0
fi
LEFT=0
[ -n "${APP:-}" ] && [ -d "$APP" ] && { echo "  ${RED}.app 仍存在：$APP${OFF}"; LEFT=1; }
[ -n "${APP:-}" ] && pgrep -qf "$APP" 2>/dev/null && { echo "  ${RED}仍有进程存活${OFF}"; LEFT=1; }
for d in "$HOME/Library/LaunchAgents"; do
    for f in "$d"/*; do
        [ -e "$f" ] || continue
        belongs "$(basename "$f")" && { echo "  ${RED}代理仍在：$f${OFF}"; LEFT=1; }
    done
done
# 沙盒容器外壳删不掉是正常现象，不算失败：容器根下的
# .com.apple.containermanagerd.metadata.plist 受 SIP 保护，rm 会报 Operation not permitted。
# 内容已经清空，剩下的外壳只有几 KB。
for f in "$HOME/Library/Containers"/*; do
    [ -e "$f" ] || continue
    belongs "$(basename "$f")" && \
        echo "  ${DIM}沙盒容器外壳残留（正常，SIP 保护，仅几 KB）：${f/#$HOME/~}${OFF}"
done
[ "$LEFT" = 0 ] && echo "  ${GRN}✓ 干净${OFF}"
