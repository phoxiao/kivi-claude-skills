# Action space & schema reference

## iphoneclaw CLI surface

| Command | Use |
|---|---|
| `doctor` | Check Screen Recording + Accessibility permissions |
| `launch` | Launch iPhone Mirroring, print window bounds |
| `bounds` | Print `x y w h` of the target window |
| `screenshot --out <path>` | Capture window to JPEG |
| `ocr --app "iPhone Mirroring" --min-confidence 0.2 --lang zh-Hans --lang en-US` | Apple Vision OCR, text + boxes |
| `script run --file <path> [--var K=V]` | Execute an action script |
| `script parse --file <path>` | Validate syntax without executing |
| `script record-user --app "iPhone Mirroring" --out <path>` | Record real mouse/scroll/hotkey into a script |
| `script from-run --run-dir runs/<id> --out <path>` | Export executed actions from a past run |
| `windows` | List visible windows (debug) |
| `calibrate` | Screenshot + coordinate mapping info |

`run` / `serve` / `ctl` belong to the VLM agent loop and are **not used** in the
deterministic layer.

## Action primitives

| Action | Notes |
|---|---|
| `click(start_box=...)` | Tap. Coordinates are normalized to the window |
| `double_click(start_box=...)` | |
| `drag(start_box=..., end_box=...)` | Sliders and reordering only |
| `scroll(direction=...)` | Incremental, mouse wheel |
| `swipe(direction=...)` | Page-level, two-finger trackpad gesture |
| `type(content=...)` | ASCII only by default — see Chinese input below |
| `hotkey(key=...)` | Keyboard shortcut |
| `iphone_home()` | Home Screen (`Cmd+1`) |
| `iphone_app_switcher()` | App Switcher (`Cmd+2`) |
| `wait()` | Sleep 5s |
| `finished()` / `call_user()` | Terminal actions |

Script composition:

```
include open_app_spotlight APP=bilibili
run_script(name='open_app_spotlight', APP='bilibili')   # equivalent explicit form
```

## iPhone Mirroring hotkeys — prefer these over coordinates

| Shortcut | Effect |
|---|---|
| `Cmd+1` | Home Screen |
| `Cmd+2` | App Switcher |
| `Cmd+3` | Spotlight search |

`Cmd+3` → type app name → Enter is the canonical way to open an app. It is
resolution-independent, survives home screen rearrangement, and costs zero visual
reasoning. **Any recorded flow that opens an app by tapping its icon should be
rewritten to use this.**

## Text anchors — how to get past the first screen

Hotkeys reach an app's front door and no further. Inside the app a recording has
nothing but coordinates, which is where flows rot. `scripts/tap_text.py` closes that
gap: OCR the window, find the box whose text matches a declared anchor, click its
centre.

```bash
python scripts/tap_text.py --any-of 签到 --any-of 立即签到 --exclude 已签到 --prefer largest
python scripts/tap_text.py --any-of 我的 --prefer bottom --dry-run
```

| Option | Meaning |
|---|---|
| `--any-of` (repeatable) | Candidate texts. First match wins, substring by default |
| `--exclude` (repeatable) | Skip boxes containing this. **Necessary**: `签到` matches `已签到` |
| `--exact` | Whole-string match instead of substring |
| `--prefer` | Tie-break among matches: `first`, `top`, `bottom`, `largest`, `shortest` |
| `--scroll` / `--scroll-max` | Scroll between retries when the anchor is below the fold |
| `--dry-run` | Print the centre it *would* tap. Always do this first on a new anchor |

Two hard refusals, and neither is retryable:

- **Denylist.** An anchor that resolves onto text containing 支付 / 买入 / 卖出 / 下单 /
  转账 / 提现 / 密码 and friends is refused, whatever the flow asked for.
- **Payment sheet.** If 请输入支付密码 / 确认支付 / 输入交易密码 is anywhere on screen,
  nothing is tapped at all — not even something unrelated.

Calibrate anchors with `scripts/screen_text.py`, which prints exactly the list
`tap_text` matches against.

## Step flows (`.json`)

A flow body may be a raw `.txt` action script or a JSON step list. Step lists exist so
taps can interleave with assertions — a `.txt` script has no way to say "wait until the
page rendered, *then* tap what it says".

`run_flow.py` dispatches on the file extension in `meta.json`.

| Step `action` | Fields | Notes |
|---|---|---|
| `open_app` | `app`, `settle` | Cmd+1 → Cmd+3 → name → Enter. Handles Chinese via clipboard |
| `tap_text` | `any_of`, `exclude`, `prefer`, `exact`, `retries`, `scroll`, `scroll_max`, `optional` | See above |
| `assert` | `type`, `value`, `retries`, `interval`, `optional` | Mid-flow gate; same types as pre/postconditions |
| `sleep` | `seconds` | Bounded by the flow's remaining `max_duration_s` |
| `scroll` | `direction`, `count` | |
| `type_text` | `text` | ASCII via `type()`, non-ASCII via clipboard |
| `hotkey` | `key` | |
| `home` | — | |
| `script` | `name`, `vars` | Run another registered flow's `.txt` body |

Two modifiers apply to any step:

- `optional: true` — a failure is recorded in the trace and the flow continues.
- `skip_if: {type, value}` — if the assertion already holds, skip the step. This is
  what makes a check-in flow genuinely idempotent: on day two the button says 已签到,
  `skip_if` matches, the tap never happens, and the postcondition still passes.

`${VAR}` is expanded in every string field from `--var` values and `vars` defaults.

## Authoring rules

1. **Hotkeys over text anchors over coordinates.** In that order. Every coordinate is a
   future breakage; every anchor is one string edit away from being fixed.
2. **Start and end at a known state.** Begin with `iphone_home()` (or an `open_app`
   step, which does it for you). Do **not** end with `home` inside the step list —
   postconditions must run on the screen that proves the intent happened. Set
   `teardown_home: true` in `meta.json` instead, which goes home after the check.
3. **One flow = one intent.** If a script does two separable things, split it.
4. **No bare waits for network.** Prefer an assertion with retry over `sleep` padding —
   padding is either too short (flaky) or too long (slow). The one legitimate `sleep` is
   a real wall-clock requirement, like 拼多多's watch-the-video timer.
5. **Coordinates are normalized** to the window, so they survive window resizing but
   *not* a different device model. Note the device in the flow's `notes` field.

## Chinese input

`IPHONECLAW_TYPE_ASCII_ONLY=1` is the default and should stay on — CGEvent-typed
Chinese drops characters. Two options:

- **Pinyin + IME**: type pinyin, then select candidates. Fragile, avoid.
- **Clipboard paste** (preferred): set the Mac clipboard, then `hotkey(key='cmd v')`.
  The Mirroring window forwards paste to the phone.

The step engine's `type_text` and `open_app` pick between these automatically: ASCII
goes through `type()`, anything else through `pbcopy` + Cmd+V. Raw `.txt` scripts get
no such help, which is why `open_app_spotlight.txt` requires a pinyin `APP`.

For Spotlight specifically, pinyin usually suffices — iOS matches Chinese app names by
pinyin, so `jingdong`, `pinduoduo`, `futu` resolve without any clipboard round trip.

## meta.json schema

Lives at `action_scripts/meta.json`, **separate from iphoneclaw's own
`registry.json`**. Do not merge them — registry.json must stay a flat `name → path`
map or the driver's parser breaks.

```json
{
  "flows": {
    "flow_name": {
      "file": "flows/flow_name.json",
      "intent": "Natural-language description of what this accomplishes. This is what the skill matches against, so write it the way a user would ask.",
      "vars": { "APP": "required", "WATCH_SECONDS": "120" },
      "preconditions":  [{ "type": "screen_contains", "value": "搜索" }],
      "postconditions": [{ "type": "screen_contains", "value": "能量" }],
      "idempotent": true,
      "verified": false,
      "teardown_home": true,
      "max_duration_s": 90,
      "notes": "Recorded on iPhone 15 Pro, iOS 18.5"
    }
  }
}
```

| Field | Meaning |
|---|---|
| `vars` | `"required"` means the caller must supply it; any other value is a default |
| `idempotent` | Decides whether a failure is retryable. Anything that sends, posts, buys, or deletes is `false` |
| `verified` | Has this replayed three times on *this* phone? `run_flow.py` refuses to run `false` without `--allow-unverified` |
| `teardown_home` | Go home after postconditions, not before |

Assertion types supported by `scripts/assert_screen.py`:

| Type | Meaning |
|---|---|
| `screen_contains` | OCR text contains `value` (substring, case-insensitive) |
| `screen_not_contains` | OCR text does not contain `value` |
| `screen_any_of` | `value` is a list; at least one matches |

## Where the library lives

The skill ships seeds in its own `action_scripts/`; `scripts/init_home.py` copies them
to `~/.iphone-automation/action_scripts/` (or `$IPHONE_AUTOMATION_HOME`), which then
takes precedence. Flows encode one person's phone, so the editable copy must not sit
inside a plugin directory that a marketplace update overwrites.

`runs/flow_log.jsonl` lands under the same home.

## Verify before trusting this file

Written against the documented CLI rather than an observed one. Confirm on first run:

1. **OCR output format.** `assert_screen.py` tries JSON first, falls back to treating
   stdout as plain text. `tap_text.py` has no fallback — without boxes it cannot work,
   and it says so rather than guessing. Run `python -m iphoneclaw ocr --app "iPhone
   Mirroring"` once, then `scripts/screen_text.py --raw`, and tighten both parsers.
2. **Box coordinate space.** `tap_text.normalise()` assumes boxes are either already
   0..1 or window-local pixels, and divides by `iphoneclaw bounds`. If they turn out to
   be screen-global, every tap lands offset by the window origin. `--dry-run` against a
   known button is the cheap way to find out — check the printed centre before arming
   anything.
3. **Variable substitution syntax inside `.txt` scripts.** `--var APP=bilibili` is
   documented, but the placeholder form inside the script body isn't; `open_app_spotlight.txt`
   guesses `${APP}`. Confirm with `script parse`. Step flows sidestep this entirely —
   `${}` expansion there happens in `run_flow.py`, not in the driver.
