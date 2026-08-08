#!/usr/bin/env python3
"""Tap whatever on screen says X — the coordinate-free tap primitive.

Why this exists
---------------
`references/action-space.md` says every baked-in coordinate is a future breakage,
and recommends hotkeys as the fix. Hotkeys only get you as far as the app's first
screen; past that, a recorded flow has nothing but coordinates. This closes that
gap without introducing a vision model: OCR the window, find the box whose text
matches a declared anchor, click the centre of that box.

The anchor ("签到") is intent. A coordinate (0.21, 0.44) is not. A flow written in
anchors survives a layout change, a device swap, and a window resize; a flow written
in coordinates survives none of them.

Deliberately duplicates assert_screen.py's OCR invocation rather than sharing it.
assert_screen is the *checker* — keeping the maker and the checker on independent
code paths is the point of the split, so a parsing bug in one cannot silently
validate the other.

Usage:
    tap_text.py --any-of 签到 --any-of 立即签到 [--prefer bottom] [--dry-run]
    tap_text.py --any-of 我的 --prefer bottom --retries 4
    tap_text.py --any-of 打卡 --scroll down --scroll-max 3

Exit 0 on a successful tap, 1 if no anchor was found, 2 on driver error or a
refusal by the safety denylist. Always prints JSON.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

APP = "iPhone Mirroring"
LANGS = ["zh-Hans", "zh-Hant", "en-US"]

TEXT_KEYS = ("text", "string", "value", "content", "label")
BOX_KEYS = ("box", "bbox", "rect", "frame", "boundingBox", "bounding_box", "bounds")
LIST_KEYS = ("items", "results", "texts", "observations", "lines", "data", "words")

# Never tap these, in any app, for any reason. A check-in flow that has drifted
# onto a purchase or transfer control is a flow that must die, not one that
# should push the button and find out.
TAP_DENYLIST = [
    "支付", "付款", "立即购买", "确认购买", "提交订单", "确认下单", "去结算",
    "立即支付", "确认支付", "去支付", "免密",
    "买入", "卖出", "下单", "交易", "开仓", "平仓", "委托",
    "充值", "提现", "转账", "转入", "转出", "开户", "借款", "借钱", "分期",
    "密码", "指纹", "面容", "face id", "touch id",
]

# If any of these are on screen we are standing in front of a payment or auth
# sheet. Do not tap anything at all — not even something that looks unrelated.
SCREEN_ABORT = [
    "请输入支付密码", "输入支付密码", "确认支付", "免密支付",
    "请输入交易密码", "输入交易密码", "指纹支付", "支付方式",
]


def run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def window_size() -> tuple[float, float]:
    """Width and height of the Mirroring window, for de-normalising OCR boxes."""
    proc = run([sys.executable, "-m", "iphoneclaw", "bounds"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "bounds failed")
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", proc.stdout)]
    if len(nums) < 4:
        raise RuntimeError(f"could not parse bounds from: {proc.stdout.strip()[:200]}")
    w, h = nums[-2], nums[-1]
    if w <= 0 or h <= 0:
        raise RuntimeError(f"nonsensical window size: {w}x{h}")
    return w, h


def run_ocr(min_confidence: float) -> object:
    cmd = [sys.executable, "-m", "iphoneclaw", "ocr",
           "--app", APP, "--min-confidence", str(min_confidence)]
    for lang in LANGS:
        cmd += ["--lang", lang]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ocr failed with no stderr")
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(
            "OCR returned non-JSON output, so no boxes are available and text "
            "anchoring cannot work. Run `python -m iphoneclaw ocr --app "
            f"\"{APP}\"` and check the format. Raw head: {proc.stdout.strip()[:200]}"
        )


def _as_box(raw) -> tuple[float, float, float, float] | None:
    """Coerce whatever shape a box arrived in into (x, y, w, h)."""
    if isinstance(raw, dict):
        keys = {k.lower(): v for k, v in raw.items()}
        if all(k in keys for k in ("x", "y")):
            x, y = keys["x"], keys["y"]
            w = keys.get("w", keys.get("width", 0))
            h = keys.get("h", keys.get("height", 0))
            return float(x), float(y), float(w), float(h)
        if all(k in keys for k in ("left", "top")):
            left, top = float(keys["left"]), float(keys["top"])
            right = float(keys.get("right", left))
            bottom = float(keys.get("bottom", top))
            return left, top, right - left, bottom - top
        return None
    if isinstance(raw, (list, tuple)) and len(raw) >= 4:
        try:
            a, b, c, d = (float(v) for v in raw[:4])
        except (TypeError, ValueError):
            return None
        # [x1,y1,x2,y2] and [x,y,w,h] are indistinguishable in general, but a
        # negative implied width means it was the corner form.
        if c >= a and d >= b and (c - a) < c and (d - b) < d:
            return a, b, c - a, d - b
        return a, b, c, d
    return None


def collect(node, out: list[dict]) -> None:
    """Walk the OCR payload gathering every {text, box} pair it contains."""
    if isinstance(node, list):
        for child in node:
            collect(child, out)
        return
    if not isinstance(node, dict):
        return

    text = next((node[k] for k in TEXT_KEYS if isinstance(node.get(k), str)), None)
    box = next((_as_box(node[k]) for k in BOX_KEYS if k in node), None)
    if text and box:
        out.append({"text": text, "box": box})
        return

    for key in LIST_KEYS:
        if key in node:
            collect(node[key], out)
            return
    for child in node.values():
        collect(child, out)


def normalise(items: list[dict], win_w: float, win_h: float) -> list[dict]:
    """Convert box centres to window-normalised 0..1 coordinates.

    Boxes already in 0..1 are passed through. Anything larger is assumed to be
    window-local pixels — see the open question in references/action-space.md;
    --dry-run exists precisely so this assumption is checked before it clicks.
    """
    out = []
    for item in items:
        x, y, w, h = item["box"]
        cx, cy = x + w / 2, y + h / 2
        if max(abs(cx), abs(cy)) > 1.0:
            cx, cy = cx / win_w, cy / win_h
        if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
            continue
        out.append({**item, "center": (round(cx, 4), round(cy, 4))})
    return out


def pick(matches: list[dict], prefer: str) -> dict:
    if prefer == "bottom":
        return max(matches, key=lambda m: m["center"][1])
    if prefer == "top":
        return min(matches, key=lambda m: m["center"][1])
    if prefer == "largest":
        return max(matches, key=lambda m: m["box"][2] * m["box"][3])
    if prefer == "shortest":
        return min(matches, key=lambda m: len(m["text"]))
    return matches[0]


def denied(text: str) -> str | None:
    low = text.casefold()
    return next((bad for bad in TAP_DENYLIST if bad.casefold() in low), None)


def click(cx: float, cy: float) -> None:
    """Issue the tap through iphoneclaw so it goes down the same path as flows."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(f"click(start_box=({cx}, {cy}))\n")
        tmp = fh.name
    try:
        proc = run([sys.executable, "-m", "iphoneclaw", "script", "run",
                    "--app", APP, "--file", tmp])
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "click failed")
    finally:
        Path(tmp).unlink(missing_ok=True)


def scroll(direction: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(f"scroll(direction='{direction}')\n")
        tmp = fh.name
    try:
        run([sys.executable, "-m", "iphoneclaw", "script", "run",
             "--app", APP, "--file", tmp])
    finally:
        Path(tmp).unlink(missing_ok=True)


def locate(anchors: list[str], prefer: str, exact: bool,
           min_confidence: float, exclude: list[str] | None = None) -> dict:
    """One OCR pass. Returns {ok, ...} without clicking anything."""
    items = []
    collect(run_ocr(min_confidence), items)
    if not items:
        return {"ok": False, "reason": "no_boxes",
                "detail": "OCR returned text but no usable boxes"}

    win_w, win_h = window_size()
    items = normalise(items, win_w, win_h)

    screen = "\n".join(i["text"] for i in items)
    low_screen = screen.casefold()
    tripped = [s for s in SCREEN_ABORT if s.casefold() in low_screen]
    if tripped:
        return {"ok": False, "reason": "refused_payment_screen", "matched": tripped,
                "detail": "a payment or credential sheet is on screen; refusing to tap"}

    # Substring matching makes 签到 match 已签到, which would tap the disabled
    # "already done" state and report success. `exclude` is how a flow says
    # "this anchor, but not that near-miss".
    blocked = [e.casefold() for e in (exclude or [])]
    live = [i for i in items if not any(b in i["text"].casefold() for b in blocked)]

    # `any_of` is a priority list, not a set: an author writing
    # ["签到领京豆", "签到"] means "the specific one, or the generic one as a
    # fallback". So anchors are the outer loop — otherwise whichever match OCR
    # happened to emit first wins, and the fallback silently beats the primary.
    def hits(anchor: str) -> list[dict]:
        a = anchor.casefold()
        if exact:
            return [i for i in live if i["text"].casefold() == a]
        return [i for i in live if a in i["text"].casefold()]

    matches: list[dict] = []
    for anchor in anchors:
        matches = hits(anchor)
        if matches:
            break

    if not matches:
        return {"ok": False, "reason": "not_found", "anchors": anchors,
                "excluded": exclude or [], "screen_excerpt": screen[:400]}

    chosen = pick(matches, prefer)
    bad = denied(chosen["text"])
    if bad:
        return {"ok": False, "reason": "refused_denylist", "text": chosen["text"],
                "matched_rule": bad,
                "detail": "anchor resolved onto a payment/trading/credential control"}

    return {"ok": True, "text": chosen["text"], "center": chosen["center"],
            "candidates": [m["text"] for m in matches][:8]}


def tap(anchors: list[str], prefer: str = "first", exact: bool = False,
        retries: int = 4, interval: float = 1.5, min_confidence: float = 0.2,
        scroll_dir: str | None = None, scroll_max: int = 0,
        dry_run: bool = False, exclude: list[str] | None = None) -> dict:
    last: dict = {}
    scrolls_used = 0
    for attempt in range(1, retries + 1):
        try:
            last = locate(anchors, prefer, exact, min_confidence, exclude)
        except Exception as exc:
            return {"ok": False, "reason": "driver_error", "detail": str(exc),
                    "attempts": attempt}

        if last["ok"]:
            cx, cy = last["center"]
            if dry_run:
                return {**last, "clicked": False, "attempts": attempt,
                        "note": "dry run — verify this centre looks right before arming"}
            click(cx, cy)
            return {**last, "clicked": True, "attempts": attempt,
                    "scrolls": scrolls_used}

        # A payment sheet or a denylisted control is terminal — retrying just
        # keeps a dangerous screen in front of an automated clicker.
        if last["reason"] in ("refused_payment_screen", "refused_denylist"):
            return {**last, "attempts": attempt}

        if attempt < retries:
            if scroll_dir and scrolls_used < scroll_max:
                scroll(scroll_dir)
                scrolls_used += 1
            time.sleep(interval)

    return {**last, "attempts": retries, "scrolls": scrolls_used}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--any-of", action="append", required=True, dest="anchors")
    ap.add_argument("--exclude", action="append", default=[],
                    help="skip boxes containing this, e.g. --any-of 签到 --exclude 已签到")
    ap.add_argument("--prefer", default="first",
                    choices=["first", "top", "bottom", "largest", "shortest"])
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--retries", type=int, default=4)
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--min-confidence", type=float, default=0.2)
    ap.add_argument("--scroll", dest="scroll_dir", choices=["up", "down"])
    ap.add_argument("--scroll-max", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    result = tap(args.anchors, args.prefer, args.exact, args.retries,
                 args.interval, args.min_confidence,
                 args.scroll_dir, args.scroll_max, args.dry_run, args.exclude)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["ok"]:
        return 0
    return 2 if result.get("reason") in ("driver_error", "no_boxes",
                                         "refused_payment_screen",
                                         "refused_denylist") else 1


if __name__ == "__main__":
    sys.exit(main())
