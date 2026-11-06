#!/bin/bash
#
# 只读审计：把一个 macOS 应用的所有残留位置列全，供卸载前决策。
#
#   用法:
#     audit-app.sh "Discord"                     按显示名
#     audit-app.sh /Applications/Discord.app     按路径
#     audit-app.sh --id com.hnc.Discord          按 bundle id（App 已删、只清残留时用）
#     audit-app.sh --all                         列出所有 App 的大小与最后使用时间
#
# 设计要点（改动前先读）:
#
#   1. bundle id 是找残留的钥匙，不是显示名。Ardot 的 id 是 com.tencent.cocraft，
#      按 "ardot" 搜 Library 只能搜到日志目录，按 id 才找得全。
#
#   2. 但**绝不能用 bundle id 的末段做子串匹配**。com.termius-dmg.mac 的末段是 "mac"，
#      拿它去 -iname "*mac*" 会命中 CleanMyMac 的特权助手和几十个系统扩展。
#      这个 bug 在第一版里真实发生过，接到卸载脚本上就是删错文件。
#      所以这里用 belongs() 做精确的结构化匹配，不做模糊子串。
#
#   3. 本脚本绝不删任何东西。删除交给 uninstall-app.sh。「看」和「动手」之间
#      必然隔着一次人的判断，是刻意的。
#
#   4. ps 对中文 App 名做八进制转义（企业微信 → M-dM-<M^A...），用 comm 字段
#      grep 中文必然假阴性。这里统一按 bundle 路径匹配进程。

set -uo pipefail

RED=$'\033[31m'; YEL=$'\033[33m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
[ -t 1 ] || { RED=""; YEL=""; DIM=""; BOLD=""; OFF=""; }

MODE="one"; TARGET=""; BY_ID=0
case "${1:-}" in
    --all) MODE="all" ;;
    --id)  BY_ID=1; TARGET="${2:-}"; [ -n "$TARGET" ] || { echo "--id 需要一个 bundle id" >&2; exit 2; } ;;
    "")    echo "用法: $0 <App名 | App路径 | --id <bundle-id> | --all>" >&2; exit 2 ;;
    *)     TARGET="$1" ;;
esac

human() { du -sh "$1" 2>/dev/null | cut -f1; }
mb()    { du -sm "$1" 2>/dev/null | cut -f1; }

# mdls 的 kMDItemLastUsedDate 经常缺失（实测 Ardot 在跑却记成空，Termius 也是空）。
# 调用方必须把它和数据目录 mtime、运行进程一起看，不能单凭它判定「没用过」。
last_used() {
    local v; v=$(mdls -name kMDItemLastUsedDate -raw "$1" 2>/dev/null)
    case "$v" in ""|"(null)") echo "-";; *) echo "${v%% *}";; esac
}

if [ "$MODE" = "all" ]; then
    printf "%8s  %-12s  %-10s  %s\n" "大小" "最后使用" "属主" "应用"
    for dir in /Applications "$HOME/Applications"; do
        [ -d "$dir" ] || continue
        for a in "$dir"/*.app; do
            [ -d "$a" ] || continue
            printf "%8s  %-12s  %-10s  %s\n" \
                "$(mb "$a")MB" "$(last_used "$a")" "$(stat -f '%Su' "$a")" "${a##*/}"
        done
    done | sort -rn
    echo
    echo "${DIM}注：「最后使用」为 - 不等于没用过，mdls 记录不全。对具体应用跑 $0 <名字> 交叉验证。${OFF}"
    [ -d /Applications/Setapp ] && echo "${YEL}注意：/Applications/Setapp 下的应用须在 Setapp 客户端里卸载，直接删会被装回。${OFF}"
    exit 0
fi

# ---- 定位 bundle -----------------------------------------------------------

APP=""
if [ "$BY_ID" = 0 ]; then
    if [ -d "$TARGET" ] && [[ "$TARGET" == *.app ]]; then
        APP="$TARGET"
    else
        for cand in "/Applications/$TARGET.app" "$HOME/Applications/$TARGET.app" "/Applications/$TARGET"; do
            [ -d "$cand" ] && { APP="$cand"; break; }
        done
        [ -n "$APP" ] || APP=$(mdfind "kMDItemContentType == 'com.apple.application-bundle' && kMDItemFSName == '$TARGET.app'" 2>/dev/null | head -1)
    fi
    BID=$([ -n "$APP" ] && plutil -extract CFBundleIdentifier raw "$APP/Contents/Info.plist" 2>/dev/null)
    DISP=$([ -n "$APP" ] && basename "$APP" .app)
else
    BID="$TARGET"
    APP=$(mdfind "kMDItemCFBundleIdentifier == '$BID'" 2>/dev/null | grep '\.app$' | head -1)
    DISP=$([ -n "$APP" ] && basename "$APP" .app)
fi

if [ -z "${BID:-}" ] && [ -z "${DISP:-}" ]; then
    echo "${RED}找不到应用 '$TARGET'。用 --id <bundle-id> 指定，或先跑 --all 看清单。${OFF}" >&2
    exit 1
fi
BID="${BID:-}"; DISP="${DISP:-}"

# ---- 归属判定（精确，不做模糊子串）-----------------------------------------
#
# 一个文件名 n 属于本应用，当且仅当满足下列之一：
#   - n == <bundleid>                       com.hnc.Discord
#   - n 以 <bundleid>. 开头                 com.hnc.Discord.helper.Renderer.plist
#   - n 以 .<bundleid> 结尾                 TEAMID.com.hnc.Discord（group container）
#   - n == <显示名>                         Discord / CherryStudio
#   - n 以 <显示名>. 或 <显示名>- 开头       Discord.plist
#   - n 的最后一个点分段 == <显示名>          HUAQ24HBR6.dev.orbstack（group container）
# 最后一条是必要的：group container 的标识符常和 bundle id 完全不同。OrbStack 的
# bundle id 是 dev.kdrag0n.MacVirt，group container 却叫 HUAQ24HBR6.dev.orbstack，
# 只按 bundle id 匹配会整个漏掉。比的是「整段相等」不是子串，所以不会误伤。
# 显示名短于 4 字符时一律不用它做匹配——"Pen"、"Zed" 这类会误伤。
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

# ---- 报告 ------------------------------------------------------------------

echo "${BOLD}=== 应用 ===${OFF}"
if [ -n "$APP" ] && [ -d "$APP" ]; then
    owner=$(stat -f '%Su' "$APP")
    printf "  路径      %s\n  大小      %s\n  属主      %s%s\n  bundle id %s\n  最后使用  %s\n" \
        "$APP" "$(human "$APP")" "$owner" \
        "$([ "$owner" != "$(id -un)" ] && printf "  %s(非当前用户，删除需 sudo)%s" "$YEL" "$OFF")" \
        "${BID:-未知}" "$(last_used "$APP")"
    case "$APP" in
        /Applications/Setapp/*) echo "  ${RED}!! Setapp 托管：必须在 Setapp 客户端里卸载，直接删会被自动装回${OFF}" ;;
        /System/*)              echo "  ${RED}!! 系统应用：不要删${OFF}" ;;
    esac
else
    echo "  ${YEL}.app 不存在（可能已删除），仅扫描残留。bundle id: $BID${OFF}"
fi

echo
echo "${BOLD}=== 运行中的进程 ===${OFF}"
FOUND_PROC=0
if [ -n "$APP" ]; then
    while IFS= read -r line; do
        FOUND_PROC=1
        # Electron/CEF 应用的命令行动辄上千字符，截断否则报告完全没法看
        if [ ${#line} -gt 110 ]; then echo "  ${line:0:110}…"; else echo "  $line"; fi
    done < <(pgrep -lf "$APP" 2>/dev/null)
fi
[ "$FOUND_PROC" = 0 ] && echo "  ${DIM}(无)${OFF}"

echo
echo "${BOLD}=== 开机代理 / 特权助手 ===${OFF}"
echo "${DIM}  卸载后进程重生的根源。带 KeepAlive 的必须先删 plist 再杀进程，否则杀了就重生。${OFF}"
FOUND_AGENT=0
for d in "$HOME/Library/LaunchAgents" /Library/LaunchAgents /Library/LaunchDaemons /Library/PrivilegedHelperTools; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
        [ -e "$f" ] || continue
        belongs "$(basename "$f")" || continue
        FOUND_AGENT=1
        flags=""
        if [[ "$f" == *.plist ]]; then
            grep -q "KeepAlive"  "$f" 2>/dev/null && flags="$flags ${RED}KeepAlive${OFF}"
            grep -q "RunAtLoad"  "$f" 2>/dev/null && flags="$flags RunAtLoad"
        fi
        case "$d" in /Library/*) flags="$flags ${YEL}(需 sudo)${OFF}" ;; esac
        echo "  $f$flags"
    done
done
[ "$FOUND_AGENT" = 0 ] && echo "  ${DIM}(无)${OFF}"

echo
echo "${BOLD}=== 数据残留 ===${OFF}"
TOTAL=0; NEWEST=0; FOUND_DATA=0
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
        FOUND_DATA=1
        sz=$(mb "$f"); TOTAL=$((TOTAL + ${sz:-0}))
        t=$(stat -f %m "$f" 2>/dev/null); [ -n "$t" ] && [ "$t" -gt "$NEWEST" ] && NEWEST=$t
        printf "  %8s  %s\n" "$(human "$f")" "${f#$HOME/}"
    done
done

# 家目录隐藏目录：最容易漏的一类。WorkBuddy 的 ~/.workbuddy 有 369M，
# 按 Library 扫一遍完全扫不到，是实测漏过的。
if [ -n "$DISP" ] && [ ${#DISP} -ge 4 ]; then
    lower=$(printf '%s' "$DISP" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
    for f in "$HOME/.$lower" "$HOME/.${lower}rc" "$HOME/.config/$lower"; do
        [ -e "$f" ] || continue
        FOUND_DATA=1
        sz=$(mb "$f"); TOTAL=$((TOTAL + ${sz:-0}))
        printf "  %8s  %s ${YEL}(家目录隐藏，易漏)${OFF}\n" "$(human "$f")" "${f#$HOME/}"
    done
fi
[ "$FOUND_DATA" = 0 ] && echo "  ${DIM}(无)${OFF}"

echo
echo "${BOLD}=== 小结 ===${OFF}"
APPMB=0; [ -n "$APP" ] && [ -d "$APP" ] && APPMB=$(mb "$APP")
printf "  App 本体 %sMB + 数据 %sMB = ${BOLD}%sMB${OFF}\n" "$APPMB" "$TOTAL" "$((APPMB + TOTAL))"
if [ "$NEWEST" -gt 0 ]; then
    echo "  数据目录最后修改：$(date -r "$NEWEST" '+%Y-%m-%d')"
    echo "  ${DIM}比 mdls 的「最后使用」可靠，但后台进程也会碰它，所以它是上界不是精确使用时间。${OFF}"
fi
[ "$FOUND_PROC" = 1 ] && echo "  ${YEL}进程在跑 —— 这个应用不是闲置的，卸载前先确认清楚${OFF}"
[ "$FOUND_AGENT" = 1 ] && echo "  ${YEL}有开机代理 —— 卸载时必须一并清理，否则 launchd 会一直拉一个不存在的程序${OFF}"
