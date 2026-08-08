#!/usr/bin/env python3
"""Execute a registered flow with assertion gates on both sides.

Every flow execution goes through here. Calling `iphoneclaw script run` directly
skips the gates, and the gates are the entire safety mechanism in a design with no
vision model — there is nothing else watching what happens on screen.

Two flow bodies are supported, dispatched on the `file` extension in meta.json:

  *.txt   a raw iphoneclaw action script, handed to `iphoneclaw script run`
  *.json  a step flow, executed here, so steps can interleave text-anchored taps
          with mid-flow assertions instead of hard-coding coordinates

Usage:
    run_flow.py <flow_name> [--var KEY=VALUE ...] [--dry-run] [--allow-unverified]
    run_flow.py --list

Prints a JSON result. status is one of:
    ok | precondition_failed | postcondition_failed | error | not_found | unverified
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from assert_screen import check  # noqa: E402
from paths import log_path, meta_path, scripts_dir  # noqa: E402
from tap_text import tap  # noqa: E402

APP = "iPhone Mirroring"


# ---------------------------------------------------------------- flow loading

def load_meta() -> dict:
    path = meta_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_flow(name: str) -> dict | None:
    return load_meta().get("flows", {}).get(name)


def resolve_vars(flow: dict, given: dict[str, str]) -> tuple[dict, list[str]]:
    """Declared vars are either the literal "required" or a default value."""
    resolved, missing = {}, []
    for key, spec in flow.get("vars", {}).items():
        if key in given:
            resolved[key] = given[key]
        elif spec == "required":
            missing.append(key)
        else:
            resolved[key] = spec
    for key, val in given.items():
        resolved.setdefault(key, val)
    return resolved, missing


def substitute(value, variables: dict[str, str]):
    """Expand ${VAR} inside step arguments."""
    if isinstance(value, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: variables.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [substitute(v, variables) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, variables) for k, v in value.items()}
    return value


# ------------------------------------------------------------------ primitives

def iphoneclaw(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "iphoneclaw", *args],
                          capture_output=True, text=True, timeout=timeout)


def run_inline(body: str, timeout: int = 60) -> None:
    """Run a couple of literal action lines through the real driver."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(body if body.endswith("\n") else body + "\n")
        tmp = fh.name
    try:
        proc = iphoneclaw(["script", "run", "--app", APP, "--file", tmp], timeout)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "action failed")
    finally:
        Path(tmp).unlink(missing_ok=True)


def type_text(text: str) -> None:
    """ASCII goes through type(); anything else goes through the clipboard.

    IPHONECLAW_TYPE_ASCII_ONLY is on by default because CGEvent-typed Chinese
    drops characters. Rather than making every caller remember that, the split
    happens here: non-ASCII is staged on the Mac clipboard and pasted, which the
    Mirroring window forwards to the phone intact.
    """
    if text.isascii():
        run_inline(f"type(content='{text}')")
        return
    proc = subprocess.run(["pbcopy"], input=text, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"pbcopy failed: {proc.stderr.strip()}")
    run_inline("hotkey(key='cmd v')")


def assert_step(step: dict) -> dict:
    value = step["value"]
    values = value if isinstance(value, list) else [value]
    return check(step.get("type", "screen_any_of"), values,
                 retries=step.get("retries", 4),
                 interval=step.get("interval", 1.5))


def run_named_script(name: str, variables: dict[str, str], timeout: int) -> None:
    flow = load_flow(name)
    if flow is None:
        raise RuntimeError(f"step referenced unknown flow: {name}")
    path = scripts_dir() / flow["file"]
    if not path.exists():
        raise RuntimeError(f"script file missing: {path}")
    args = ["script", "run", "--app", APP, "--file", str(path)]
    for key, val in variables.items():
        args += ["--var", f"{key}={val}"]
    proc = iphoneclaw(args, timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "script failed")


# ----------------------------------------------------------------- step engine

def execute_steps(body: dict, variables: dict[str, str], deadline: float) -> dict:
    """Run a step flow. Returns {ok, ...}; a failed step names itself."""
    trace: list[dict] = []

    for index, raw in enumerate(body.get("steps", [])):
        if time.time() > deadline:
            return {"ok": False, "detail": "flow exceeded max_duration_s",
                    "failed_step": index, "trace": trace}

        step = substitute(raw, variables)
        action = step.get("action")
        label = {"step": index, "action": action}

        # Check-in flows are idempotent precisely because they no-op when the
        # thing is already done. `skip_if` is how a step says "the goal state is
        # already on screen" without treating that as a failure.
        guard = step.get("skip_if")
        if guard:
            values = guard["value"] if isinstance(guard["value"], list) else [guard["value"]]
            hit = check(guard.get("type", "screen_any_of"), values,
                        retries=guard.get("retries", 1),
                        interval=guard.get("interval", 0.5))
            if hit["ok"]:
                trace.append({**label, "skipped": "skip_if matched",
                              "value": guard["value"]})
                continue

        try:
            if action == "home":
                run_inline("iphone_home()")

            elif action == "open_app":
                run_inline("iphone_home()")
                run_inline("hotkey(key='cmd 3')")
                time.sleep(step.get("settle", 1.2))
                type_text(step["app"])
                time.sleep(step.get("settle", 1.2))
                run_inline("hotkey(key='enter')")
                label["app"] = step["app"]

            elif action == "script":
                run_named_script(step["name"], step.get("vars", {}),
                                 int(max(5, deadline - time.time())))
                label["name"] = step["name"]

            elif action == "tap_text":
                result = tap(step["any_of"],
                             prefer=step.get("prefer", "first"),
                             exact=step.get("exact", False),
                             retries=step.get("retries", 4),
                             interval=step.get("interval", 1.5),
                             scroll_dir=step.get("scroll"),
                             scroll_max=step.get("scroll_max", 0),
                             exclude=step.get("exclude"))
                label["result"] = result
                if not result["ok"]:
                    if step.get("optional"):
                        label["skipped"] = True
                    else:
                        trace.append(label)
                        return {"ok": False, "detail":
                                f"tap_text failed on {step['any_of']}: {result.get('reason')}",
                                "failed_step": index, "trace": trace}

            elif action == "assert":
                result = assert_step(step)
                label["result"] = {k: result[k] for k in ("ok", "reason", "attempts")
                                   if k in result}
                if not result["ok"]:
                    if step.get("optional"):
                        label["skipped"] = True
                    else:
                        trace.append(label)
                        return {"ok": False,
                                "detail": f"in-flow assertion failed: {step.get('value')}",
                                "failed_step": index, "trace": trace,
                                "screen_excerpt": result.get("screen_excerpt", "")}

            elif action == "sleep":
                seconds = float(step.get("seconds", 5))
                label["seconds"] = seconds
                time.sleep(min(seconds, max(0.0, deadline - time.time())))

            elif action == "scroll":
                count = int(step.get("count", 1))
                body_lines = "\n".join(
                    f"scroll(direction='{step.get('direction', 'down')}')"
                    for _ in range(count))
                run_inline(body_lines)

            elif action == "type_text":
                type_text(step["text"])

            elif action == "hotkey":
                run_inline(f"hotkey(key='{step['key']}')")

            else:
                return {"ok": False, "detail": f"unknown step action: {action}",
                        "failed_step": index, "trace": trace}

        except Exception as exc:
            trace.append({**label, "error": str(exc)})
            return {"ok": False, "detail": str(exc), "failed_step": index,
                    "trace": trace}

        trace.append(label)

    return {"ok": True, "trace": trace}


# ---------------------------------------------------------------- flow running

def run_assertions(assertions: list[dict], phase: str) -> dict | None:
    """Return the first failure, or None if all pass."""
    for spec in assertions:
        value = spec["value"]
        values = value if isinstance(value, list) else [value]
        result = check(spec["type"], values,
                       retries=spec.get("retries", 3),
                       interval=spec.get("interval", 1.5))
        if not result["ok"]:
            return {"phase": phase, "assertion": spec, "result": result}
    return None


def execute(flow: dict, variables: dict[str, str]) -> dict:
    path = scripts_dir() / flow["file"]
    if not path.exists():
        return {"ok": False, "detail": f"flow body missing: {path}"}

    budget = flow.get("max_duration_s", 120)

    if path.suffix == ".json":
        body = json.loads(path.read_text(encoding="utf-8"))
        return execute_steps(body, variables, deadline=time.time() + budget)

    args = ["script", "run", "--app", APP, "--file", str(path)]
    for key, val in variables.items():
        args += ["--var", f"{key}={val}"]
    try:
        proc = iphoneclaw(args, timeout=budget)
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": "flow exceeded max_duration_s"}
    if proc.returncode != 0:
        return {"ok": False, "detail": (proc.stderr.strip() or proc.stdout.strip())[:800]}
    return {"ok": True, "stdout": proc.stdout.strip()[:800]}


def log(record: dict) -> None:
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def list_flows() -> int:
    flows = load_meta().get("flows", {})
    out = {name: {"intent": f.get("intent", ""),
                  "vars": f.get("vars", {}),
                  "idempotent": f.get("idempotent", False),
                  "verified": f.get("verified", False)}
           for name, f in flows.items()}
    print(json.dumps({"library": str(scripts_dir()), "flows": out},
                     ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("flow", nargs="?")
    ap.add_argument("--var", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="run a flow that has not yet passed 3 replays on this phone")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        return list_flows()
    if not args.flow:
        ap.error("flow name required (or --list)")

    given = dict(v.split("=", 1) for v in args.var)
    started = time.time()

    flow = load_flow(args.flow)
    if flow is None:
        print(json.dumps({"status": "not_found", "flow": args.flow,
                          "hint": f"run --list against {meta_path()}"},
                         ensure_ascii=False, indent=2))
        return 1

    variables, missing = resolve_vars(flow, given)
    if missing:
        print(json.dumps({"status": "error", "flow": args.flow,
                          "detail": f"missing required vars: {missing}"},
                         ensure_ascii=False, indent=2))
        return 1

    # Gate 2 of iphone-script-forge, enforced instead of documented. A flow
    # authored against an app's *expected* layout is a hypothesis until it has
    # replayed on this particular phone.
    if not flow.get("verified", False) and not args.allow_unverified and not args.dry_run:
        print(json.dumps({
            "status": "unverified", "flow": args.flow,
            "detail": "flow has not been replay-tested on this phone",
            "hint": "calibrate anchors first with scripts/screen_text.py against the "
                    "real screens, then run --allow-unverified three times; flip "
                    "\"verified\": true in meta.json once all three pass",
            "notes": flow.get("notes", ""),
        }, ensure_ascii=False, indent=2))
        return 1

    result: dict = {
        "flow": args.flow,
        "vars": variables,
        "idempotent": flow.get("idempotent", False),
        "verified": flow.get("verified", False),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    failure = run_assertions(flow.get("preconditions", []), "precondition")
    if failure:
        result |= {"status": "precondition_failed", "failure": failure}
    elif args.dry_run:
        result |= {"status": "ok", "note": "dry run — preconditions only, nothing executed"}
    else:
        outcome = execute(flow, variables)
        if not outcome["ok"]:
            result |= {"status": "error", "detail": outcome["detail"],
                       "failed_step": outcome.get("failed_step"),
                       "trace": outcome.get("trace")}
        else:
            failure = run_assertions(flow.get("postconditions", []), "postcondition")
            if failure:
                # Note for the caller: a postcondition failure on a non-idempotent
                # flow means unknown side effects. It is not retryable.
                result |= {"status": "postcondition_failed", "failure": failure}
            else:
                result |= {"status": "ok"}

        # Postconditions are checked on the app screen that proves the intent
        # happened, so the trip home comes after, not before.
        if flow.get("teardown_home"):
            try:
                run_inline("iphone_home()")
            except Exception as exc:
                result["teardown_error"] = str(exc)

    result["duration_s"] = round(time.time() - started, 1)
    log(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
