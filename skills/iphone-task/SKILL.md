---
name: iphone-task
description: Execute tasks on a real iPhone through the macOS iPhone Mirroring window using pre-registered deterministic action scripts. Use this skill whenever a task requires operating the user's actual phone — opening an iOS app, tapping through a flow, checking in (京东签到 / 拼多多打卡 / 富途签到), collecting something, reading information that only exists on the phone, or any request phrased like "在手机上…", "帮我看下手机", "打开 App 做 X", "签到". Trigger it even when the user does not mention iPhone Mirroring or automation by name. Also use it when the user asks what phone flows are currently available or why a phone flow failed.
---

# iPhone Task (deterministic layer)

Runs registered action scripts against the iPhone Mirroring window via the `iphoneclaw` CLI.
There is **no vision model in this loop**. Every action executed is one that a human
previously recorded, or one anchored to text that OCR can actually see on screen.

## The one rule that matters

**If no registered flow matches the task, stop. Do not improvise coordinates.**

Without a VLM there is no way to look at the screen and decide where to tap. Guessing
`click(start_box=...)` values on a live phone is how you end up sending a message,
confirming a payment, or deleting something. When there is no match, report what
flows *do* exist and offer to record a new one (see "When nothing matches").

Text anchors are the one sanctioned exception, and they are not an exception to the
rule so much as its point: `tap_text` clicks the box that *says* 签到, wherever that
box happens to be. It never invents a position.

## Preflight

Run once per session, before the first flow:

```bash
python -m iphoneclaw doctor        # Screen Recording + Accessibility must both be OK
python -m iphoneclaw launch        # brings up iPhone Mirroring, prints window bounds
```

If `doctor` reports MISSING, stop and tell the user to grant the permission to their
terminal app in System Settings > Privacy & Security. Do not attempt to work around it.

If `launch` cannot find the window, the phone is probably unlocked or out of range —
iPhone Mirroring requires the phone locked and nearby. Say so plainly rather than retrying.

First time only, copy the seed flow library somewhere editable:

```bash
python .claude/skills/iphone-task/scripts/init_home.py
```

Flows live in `~/.iphone-automation/action_scripts/` after that (override with
`$IPHONE_AUTOMATION_HOME`). Before it is seeded, the bundled copy inside the skill is
used read-only — fine for a first run, but anchor edits belong in the user copy or a
plugin update wipes them.

## Executing a flow

1. **Match the task to a flow.** Read `action_scripts/meta.json`, or:

```bash
python .claude/skills/iphone-task/scripts/run_flow.py --list
```

   Match on the flow's `intent` field, not on its name. If two flows plausibly match,
   ask which one — do not pick.

2. **Fill required variables.** A var whose value is the literal `"required"` must be
   supplied; anything else is a default you may leave alone. Ask for missing ones
   rather than inventing them.

3. **Run it:**

```bash
python .claude/skills/iphone-task/scripts/run_flow.py <flow_name> --var KEY=VALUE
```

   This wrapper checks preconditions, executes the body, checks postconditions, and
   emits a JSON result. Do not call `python -m iphoneclaw script run` directly — that
   bypasses the assertion gates, which are the only safety mechanism in this design.

4. **Interpret the result.** The JSON has `status` of `ok`, `precondition_failed`,
   `postcondition_failed`, `unverified`, `error`, or `not_found`.

## Registered flows

| Flow | Intent | Verified | Idempotent |
|---|---|---|---|
| `reset_home` | 回到桌面（恢复用） | yes | yes |
| `open_app_spotlight` | 按名字打开 App | yes | yes |
| `jd_checkin` | 京东签到领京豆 | **no** | yes |
| `pdd_video_checkin` | 拼多多多多视频打卡 | **no** | yes |
| `futu_checkin` | 富途牛牛签到领牛币 | **no** | yes |

The three check-in flows were authored from each app's expected layout, not recorded
from a phone. Their text anchors are a hypothesis until they replay. `run_flow.py`
refuses to run them until `verified: true` — see "Arming an unverified flow".

## Arming an unverified flow

Three steps, roughly five minutes per flow, and it only has to happen once per app.

1. **Check the anchors against the real screen.** Open the app by hand, park it on the
   screen the flow needs to reach, and dump what OCR actually sees:

```bash
python .claude/skills/iphone-task/scripts/screen_text.py --grep 签
```

   Every line is `(x, y)  text` — the same list `tap_text` matches against. If the
   button says 立即签到 and the flow says 签到, edit the `any_of` list in
   `action_scripts/flows/<name>.json`. **Edit the strings, never add coordinates.**

2. **Replay it three times from a cold start.** This is Gate 2 of `iphone-script-forge`:

```bash
python .claude/skills/iphone-task/scripts/run_flow.py jd_checkin --allow-unverified
```

   Day one it should check in; days two and three the `skip_if` guards should make it
   a no-op that still ends `ok`. Both outcomes count as a pass — a check-in flow that
   *can't* no-op isn't idempotent, whatever its flag says.

3. **Flip the flag.** Set `"verified": true` in `meta.json` once three runs pass. One
   failure means fix the anchors and start the count over. Do not loosen a
   postcondition to get a pass — that converts a caught failure into an uncaught one.

## Failure handling

| Result | What it means | What to do |
|---|---|---|
| `unverified` | Flow has never replayed on this phone | Run "Arming an unverified flow". Do not just pass `--allow-unverified` and move on |
| `precondition_failed` | Phone isn't in the expected starting state | Run the `reset_home` flow, retry **once** |
| `postcondition_failed` + flow is `idempotent: true` | Flow may have partially run | Retry **once**, then stop and report |
| `postcondition_failed` + flow is `idempotent: false` | Unknown side effects may have occurred | **Stop immediately.** Never retry. Report exactly which step's assertion failed and ask the user to check the phone |
| `error` with `failed_step` | A step flow died mid-way | The `trace` names the step and the anchor it couldn't find. That's a calibration problem, not a retry problem |
| `error` | Driver/CLI problem | Report stderr verbatim, do not retry |

Two retries total per task, ever. If you're on the third attempt, the flow is broken —
that's a `iphone-script-forge` problem, not something to push through.

Three refusals are terminal and must never be retried or worked around:
`refused_payment_screen`, `refused_denylist`, and any `screen_not_contains` assertion
tripping on 买入/卖出/下单/委托. They mean the flow drifted somewhere it must not
click. Report where it landed and stop.

## When nothing matches

Say which flows exist and what they do, then offer the recording path:

```bash
python -m iphoneclaw script record-user --app "iPhone Mirroring" \
  --out action_scripts/candidates/<name>.txt
```

The user performs the flow by hand once; recording stops on Ctrl-C. Then hand off to
the **iphone-script-forge** skill to turn the raw recording into an admitted flow.
Do not register a raw recording yourself — it hasn't been reviewed or replay-tested.

## Constraints to surface proactively

Mention these when relevant rather than letting the user discover them by failure:

- **Focus is exclusive.** macOS routes input to the frontmost app, so the driver
  activates iPhone Mirroring before every action. The user cannot use the Mac for
  anything else while a flow runs. `pdd_video_checkin` idles two full minutes watching
  video — say so before starting it, not after.
- **Picking up the phone kills the session.** Any flow in progress will fail mid-way.
- **Non-ASCII typing is blocked by default** (`IPHONECLAW_TYPE_ASCII_ONLY=1`). The step
  engine's `open_app` and `type_text` route Chinese through the clipboard automatically;
  raw `.txt` scripts still can't type it.
- **Blocked apps.** Refuse to run or record flows touching payment, banking, or
  password entry, even if a script for one exists. Say why. `futu_checkin` is allowed
  because 签到 earns points and moves no money — but it runs inside a brokerage, which
  is why it asserts its way past the trading screens rather than trusting them not to
  appear.

## Reference

- `references/action-space.md` — action primitives, step-flow schema, iPhone Mirroring
  hotkeys, iphoneclaw CLI surface, meta.json schema. Read this before authoring or
  debugging a flow.
