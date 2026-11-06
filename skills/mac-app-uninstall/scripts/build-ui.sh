#!/bin/bash
# 把 scan-all.py 产出的 apps.json 注入 assets/uninstaller.html，生成自包含界面。
#   用法: build-ui.sh <apps.json> [输出.html]
set -euo pipefail
JSON="${1:?用法: build-ui.sh <apps.json> [输出.html]}"
OUT="${2:-./uninstaller.html}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 - "$JSON" "$DIR/assets/uninstaller.html" "$OUT" "$DIR/scripts/uninstall-app.sh" "$(id -un)" <<'PY'
import json, sys
data_path, tpl_path, out_path, script_path, me = sys.argv[1:6]
data = json.load(open(data_path, encoding="utf-8"))
data["script"] = script_path
tpl = open(tpl_path, encoding="utf-8").read()
html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__ME__", me)
open(out_path, "w", encoding="utf-8").write(html)
print(f"已生成 {out_path}（{len(data['apps'])} 个应用）")
PY
