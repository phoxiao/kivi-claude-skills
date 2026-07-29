#!/bin/bash
#
# 部署磁盘清理定时任务（launchd）。改完脚本或 plist 后重跑即可生效。
#
#   ./install-cron.sh            安装或更新
#   ./install-cron.sh --uninstall 卸载
#
# 为什么「拷贝」而非「软链」——两个坑（pitfalls L1/L2）：
#   L1: launchd 拒绝 LaunchAgents 下的软链 plist（bootstrap 报 5: I/O error）。
#   L2: 脚本留在外置盘会被 TCC 挡住（launchd 的 bash 无 FDA → exit 126）。
#   所以：skill/仓库是源码，本脚本把它们落到内置盘的运行位置。
#
set -euo pipefail

LABEL="local.disk-cleanup"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DST="$HOME/.local/bin/disk-cleanup-caches.sh"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "--uninstall" ]; then
    launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
    rm -f "$PLIST_DST" "$SCRIPT_DST"
    echo "已卸载 ${LABEL}"
    exit 0
fi

mkdir -p "$(dirname "$SCRIPT_DST")" "$(dirname "$PLIST_DST")"

# 1) 脚本 → 内置盘
install -m 755 "$SRC_DIR/cleanup-caches.sh" "$SCRIPT_DST"
echo "✓ 脚本  → $SCRIPT_DST"

# 2) plist → LaunchAgents，__HOME__ 占位符换真实家目录（plist 不展开 ~/$HOME，pitfalls L5）
sed "s|__HOME__|$HOME|g" "$SRC_DIR/disk-cleanup.plist.tmpl" > "$PLIST_DST"
chmod 644 "$PLIST_DST"
plutil -lint "$PLIST_DST" > /dev/null
echo "✓ plist → $PLIST_DST"

# 3) 重新加载
launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST_DST"
echo "✓ 已加载 ${LABEL}（每天 13:00 检查）"

echo
echo "试跑(不删):    $SCRIPT_DST --dry-run"
echo "立即清(忽略阈值): $SCRIPT_DST --force"
echo "让 launchd 触发: launchctl kickstart -p gui/$UID/${LABEL}"
echo "看日志:        tail -f ~/Library/Logs/disk-cleanup.log"
