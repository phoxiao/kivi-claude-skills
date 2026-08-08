---
name: iphone-script-forge
description: Turn a raw iPhone Mirroring recording into a reviewed, replay-tested, registered flow. Use this skill after the user has recorded a phone interaction with `script record-user`, when a registered flow keeps failing and needs repair, when the user says a phone flow is brittle or broken, or when they ask to add/promote/register a new phone automation. Also use it when reviewing what is sitting in action_scripts/candidates/ waiting for admission.
---

# iPhone Script Forge

Promotes `action_scripts/candidates/*.txt` into admitted entries in
`action_scripts/meta.json`. Nothing reaches `meta.json` without passing all three
gates below.

The point of this skill is to resist the obvious shortcut: a recording that worked
once looks like a working flow. It isn't. It's one sample of a process whose variance
you haven't measured, with coordinates baked in from one particular home screen layout
on one particular device.

## Gate 1 — Rewrite coordinates into intent

Read the raw recording and replace positional actions with deterministic ones wherever
possible. Read `../iphone-task/references/action-space.md` for the primitives.

The highest-value rewrite, and the one to always look for first:

```
# recorded — breaks when the home screen is rearranged
iphone_home()
click(start_box=(0.21, 0.44))

# rewritten — resolution and layout independent
iphone_home()
hotkey(key='cmd 3')
type(content='Bilibili')
hotkey(key='enter')
```

Past the app's front door, hotkeys run out and only coordinates are left. That is what
`tap_text` is for — the second-best rewrite, and the one that applies to most of a
recording's body:

```
# recorded — breaks when the button moves, or the app reflows the page
click(start_box=(0.50, 0.72))

# rewritten as a step flow — clicks whatever box says 签到, wherever it is
{"action": "tap_text", "any_of": ["立即签到", "签到"], "exclude": ["已签到"]}
```

A recording that is one long `click()` sequence usually wants to become a `.json` step
flow rather than a cleaned-up `.txt`. See the step-flow table in
`../iphone-task/references/action-space.md`.

Also do:
- Collapse repeated `wait()` padding into a postcondition assertion with retry.
- Wrap taps that a repeat run would find already-done in `skip_if`, so the flow is
  idempotent in fact and not just in flag.
- Split the script if it accomplishes two separable intents.
- Add `iphone_home()` at the start and end so the flow is composable.
- Extract literals that vary between runs into `--var` parameters.

Validate syntax before going further:

```bash
python -m iphoneclaw script parse --file action_scripts/candidates/<name>.txt
```

## Gate 2 — Attach assertions, then replay

Write the `preconditions` / `postconditions` for the flow. This is the step people
skip, and it's the one that makes the difference between a flow that fails loudly and
one that fails silently having done half its work.

A good postcondition names the *observable consequence*, not the final screen:

- Weak: `screen_contains: 首页` — true of many states, including failure states
- Strong: `screen_contains: 已签到` — only true if the thing actually happened

Then replay three times from a cold start (`iphone_home()` between runs):

```bash
for i in 1 2 3; do
  python .claude/skills/iphone-task/scripts/run_flow.py <name> --allow-unverified --var K=V
done
```

Three passes is the admission bar, and it is enforced rather than trusted: a flow sits
at `"verified": false` in `meta.json` until then, and `run_flow.py` refuses to run it
without `--allow-unverified`. Flipping the flag is the admission.

One failure means back to Gate 1 — do not "fix" it by loosening the assertion, which
converts a caught failure into an uncaught one.

For a daily check-in flow, "three passes" spans three days, and days two and three
should be *no-ops that still end `ok`*. A check-in flow that cannot no-op is not
idempotent, whatever the flag says — send it back for `skip_if` guards.

## Gate 3 — Human review of intent, not source

Present the user with a summary, not the script body:

```
Flow: ant_forest_collect
Intent: 收取蚂蚁森林能量
Steps:  home → spotlight "Alipay" → tap 蚂蚁森林 entry → collect loop ×5 → home
Pre:    screen_contains 桌面
Post:   screen_contains 能量
Idempotent: true    Replays: 3/3 passed    Coordinates remaining: 2
Device: iPhone 15 Pro / iOS 18.5
```

`Coordinates remaining` counts literal `click(start_box=...)` calls. A `tap_text` step
is not a coordinate — it resolves its position from the screen every run, so it does
not contribute to the fragility score.

Then ask directly: **does each remaining coordinate have a reason it can't be a
hotkey, and does the postcondition prove the intent actually happened?**

Report `Coordinates remaining` honestly — it is the flow's fragility score, and
watching it trend down across the library is the point of this whole layer.

If the user can't tell from the summary what the flow does, that's the signal it
encodes positions rather than intent. Send it back to Gate 1 rather than admitting it.

## Admission

On approval: move the file into the live library (`recorded/` for `.txt` bodies,
`flows/` for `.json` step flows), add the entry to `meta.json` with
`"verified": true`, and add the flat `name → path` entry to iphoneclaw's own
`registry.json`. Keep the two files separate — `registry.json` must stay a flat map or
the driver's parser breaks.

The live library is `~/.iphone-automation/action_scripts/` (or
`$IPHONE_AUTOMATION_HOME`), **not** the copy bundled inside the iphone-task skill — a
marketplace update overwrites the bundle.

Set `idempotent: false` for anything that sends, posts, buys, deletes, or otherwise
has effects that a retry would duplicate. When in doubt, `false` — the cost of a
wrongly-false flag is one manual retry, the cost of a wrongly-true flag is a duplicate
side effect on someone's real phone.

## Repairing an admitted flow

When an existing flow starts failing, read `runs/flow_log.jsonl` first — the failing
assertion tells you where it broke and usually why. Then move it back to
`candidates/`, remove it from `meta.json` so it can't be run mid-repair, and re-enter
at Gate 1.
