#!/usr/bin/env python3
"""Print what OCR currently sees, with normalised tap coordinates.

This is the calibration tool. When a flow's anchor doesn't match — the button now
says 立即签到 instead of 签到, or the OCR splits it across two boxes — open the app
by hand, park it on the screen in question, and run this. Whatever it prints is
exactly what `tap_text` gets to work with, so the anchors in the flow file can be
edited to match reality rather than to match a guess.

Usage:
    screen_text.py                 # every box, top to bottom
    screen_text.py --grep 签到      # only boxes containing this
    screen_text.py --raw           # unparsed OCR output, for debugging the parser
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tap_text import collect, normalise, run_ocr, window_size  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grep")
    ap.add_argument("--min-confidence", type=float, default=0.2)
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        payload = run_ocr(args.min_confidence)
    except Exception as exc:
        print(json.dumps({"ok": False, "detail": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    if args.raw:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    items: list[dict] = []
    collect(payload, items)
    if not items:
        print(json.dumps({"ok": False, "reason": "no_boxes",
                          "detail": "OCR gave text but no boxes — tap_text cannot work; "
                                    "re-check the parser against --raw output"},
                         ensure_ascii=False, indent=2))
        return 2

    win_w, win_h = window_size()
    items = normalise(items, win_w, win_h)
    items.sort(key=lambda i: (i["center"][1], i["center"][0]))

    if args.grep:
        needle = args.grep.casefold()
        items = [i for i in items if needle in i["text"].casefold()]

    if args.json:
        print(json.dumps({"ok": True, "window": [win_w, win_h], "items": items},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"window {win_w:.0f}x{win_h:.0f}, {len(items)} box(es)")
    for item in items:
        cx, cy = item["center"]
        print(f"  ({cx:.3f}, {cy:.3f})  {item['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
