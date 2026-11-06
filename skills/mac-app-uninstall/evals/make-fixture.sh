#!/bin/bash
# 造一个假应用当测试夹具：完整残留结构 + 一个 KeepAlive 的 LaunchAgent。
# 名字刻意取得不可能撞车。teardown 用 --clean。
set -euo pipefail
N="${FIXTURE_NAME:-ZzFixtureApp}"
DISP="$N"; BID="io.zzfixture.$(printf "%s" "$N" | tr "[:upper:]" "[:lower:]")"; TEAM="ZZ0000TEST"
APP="$HOME/Applications/$DISP.app"
AGENT="$HOME/Library/LaunchAgents/$BID.helper.plist"
PATHS=(
  "$HOME/Library/Application Support/$DISP"
  "$HOME/Library/Containers/$BID"
  "$HOME/Library/Group Containers/$TEAM.$BID"
  "$HOME/Library/Caches/$BID"
  "$HOME/Library/Preferences/$BID.plist"
  "$HOME/Library/HTTPStorages/$BID"
  "$HOME/Library/Logs/$DISP"
  "$HOME/.$(printf "%s" "$N" | tr "[:upper:]" "[:lower:]")"
)
if [ "${1:-}" = "--clean" ]; then
  launchctl bootout "gui/$(id -u)/$BID.helper" 2>/dev/null || true
  rm -rf "$APP" "$AGENT"; for p in "${PATHS[@]}"; do rm -rf "$p"; done
  echo "夹具已清除"; exit 0
fi
mkdir -p "$APP/Contents/MacOS"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>$BID</string>
<key>CFBundleName</key><string>$DISP</string>
<key>CFBundleExecutable</key><string>$DISP</string>
</dict></plist>
PLIST
printf '#!/bin/bash\nwhile true; do sleep 60; done\n' > "$APP/Contents/MacOS/$DISP"
chmod +x "$APP/Contents/MacOS/$DISP"
for p in "${PATHS[@]}"; do
  case "$p" in *.plist) printf '{}' > "$p" ;; *) mkdir -p "$p"; dd if=/dev/zero of="$p/blob.bin" bs=1m count=6 2>/dev/null ;; esac
done
mkdir -p "$(dirname "$AGENT")"
cat > "$AGENT" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$BID.helper</string>
<key>ProgramArguments</key><array><string>$APP/Contents/MacOS/$DISP</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
</dict></plist>
PLIST
launchctl bootstrap "gui/$(id -u)" "$AGENT" 2>/dev/null || launchctl load "$AGENT" 2>/dev/null || true
sleep 2
echo "夹具就绪：$DISP ($BID)"
pgrep -f "$APP" >/dev/null && echo "  守护进程已启动（KeepAlive 生效）" || echo "  守护进程未启动"
