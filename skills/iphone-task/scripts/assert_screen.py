#!/usr/bin/env python3
"""OCR-based screen assertion for the iPhone Mirroring deterministic layer.

This is the checker half of the maker/checker split: the action script is the maker,
this is the checker. It is deliberately NOT a model — it is a substring match over
Apple Vision OCR output, so its failure modes are uncorrelated with whatever produced
the action.

Usage:
    assert_screen.py --type screen_contains --value "能量"
    assert_screen.py --type screen_any_of --value "签到" --value "已签到"

Exit 0 if the assertion holds, 1 if it does not, 2 on driver error.
Always prints a JSON object to stdout.
"""

import argparse
import json
import subprocess
import sys
import time

APP = "iPhone Mirroring"
LANGS = ["zh-Hans", "zh-Hant", "en-US"]
TEXT_KEYS = ("text", "string", "value", "content")
LIST_KEYS = ("items", "results", "texts", "observations", "lines", "data")


def run_ocr(min_confidence: float) -> str:
    """Return raw stdout from the OCR command. Raises on non-zero exit."""
    cmd = [sys.executable, "-m", "iphoneclaw", "ocr",
           "--app", APP, "--min-confidence", str(min_confidence)]
    for lang in LANGS:
        cmd += ["--lang", lang]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ocr failed with no stderr")
    return proc.stdout


def extract_text(stdout: str) -> str:
    """Flatten OCR output to a single searchable string.

    The exact JSON shape is unconfirmed (see references/action-space.md), so this
    walks whatever structure comes back and falls back to raw text. Tighten it once
    the real format is known — a looser parser here means false-positive assertions,
    which is the dangerous direction.
    """
    stripped = stdout.strip()
    if not stripped:
        return ""
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped

    collected: list[str] = []

    def walk(node) -> None:
        if isinstance(node, str):
            collected.append(node)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            hit = [node[k] for k in TEXT_KEYS if isinstance(node.get(k), str)]
            if hit:
                collected.extend(hit)
                return
            for key in LIST_KEYS:
                if key in node:
                    walk(node[key])
                    return
            for child in node.values():
                walk(child)

    walk(parsed)
    return "\n".join(collected) if collected else stripped


def evaluate(kind: str, values: list[str], screen: str) -> bool:
    haystack = screen.casefold()
    needles = [v.casefold() for v in values]
    if kind == "screen_contains":
        return all(n in haystack for n in needles)
    if kind == "screen_not_contains":
        return not any(n in haystack for n in needles)
    if kind == "screen_any_of":
        return any(n in haystack for n in needles)
    raise ValueError(f"unknown assertion type: {kind}")


def check(kind: str, values: list[str], retries: int = 3,
          interval: float = 1.5, min_confidence: float = 0.2) -> dict:
    """Retry loop absorbs transition animations and network latency.

    A negative assertion (screen_not_contains) that passes on the first read is not
    retried — it is already satisfied. Positive assertions retry because the thing
    being waited for may not have rendered yet.
    """
    last_screen = ""
    for attempt in range(1, retries + 1):
        try:
            last_screen = extract_text(run_ocr(min_confidence))
        except Exception as exc:
            return {"ok": False, "reason": "ocr_error", "detail": str(exc),
                    "attempts": attempt}
        if evaluate(kind, values, last_screen):
            return {"ok": True, "type": kind, "value": values,
                    "attempts": attempt, "screen_excerpt": last_screen[:400]}
        if attempt < retries:
            time.sleep(interval)
    return {"ok": False, "reason": "assertion_failed", "type": kind,
            "value": values, "attempts": retries,
            "screen_excerpt": last_screen[:400]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True,
                    choices=["screen_contains", "screen_not_contains", "screen_any_of"])
    ap.add_argument("--value", action="append", required=True)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--min-confidence", type=float, default=0.2)
    args = ap.parse_args()

    result = check(args.type, args.value, args.retries,
                   args.interval, args.min_confidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["ok"]:
        return 0
    return 2 if result.get("reason") == "ocr_error" else 1


if __name__ == "__main__":
    sys.exit(main())
