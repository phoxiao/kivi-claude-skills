# The verification gate

The gate is the loop's anti-bullshit mechanism. **The orchestrator runs it
itself, in the main context** — never the implementer, never a subagent that just
reports back "green." The reason is structural: the exit code that decides commit
vs rollback must be a fact you observed, not a claim you were handed.

## Why the orchestrator runs it (not the implementer)

- **Confirmation bias.** A subagent that just wrote the code has a context full of
  "here's why this is right." It will run to green and declare success. That is
  exactly how "wrote the service, assumed it was wired, UI never calls it" ships.
- **The result must drive a decision in your context.** You hold the commit power.
  If verification runs inside a subagent, all you get back is a sentence ("tests
  pass") — a claim filtered through another context. To not blindly trust it, you
  must run the command and see the exit code yourself.
- **It's cheap.** `test` / `build` / `grep` are deterministic — no reasoning, near
  zero context cost. Spawning a subagent for them is pure overhead and adds a
  fidelity-losing summarization layer.

Rule of thumb: **deterministic + result-drives-your-decision → run it yourself;
judgment + wants-independent-eyes → subagent.** The one exception: when
verification fails for an *unclear* reason, spawn a debug subagent — diagnosis is
judgment work.

## What the gate checks

1. **Authoritative test command, fully green.** Pick the *one* command whose exit
   code is the source of truth (e.g. `swift test`, `pytest -q`, `go test ./...`,
   `cargo test`). Prefer the fastest layer that still covers the change's logic.
   If your test setup has a known false-failure (a simulator quirk, a flaky
   integration suite under load), name it in the queue header and treat the
   authoritative command's result as truth — don't let a known false-failure
   flip your verdict, and don't let it excuse a real one.
2. **Build(s) succeed.** Every target/platform the change touches must compile.
   "Tests pass in one module" doesn't prove the app links.
3. **Wiring grep — the special one.** For any task that connects a producer to a
   consumer (a View to a ViewModel/service, a handler to a route, a new function
   to its caller), grep the diff/tree to assert the consumer *actually calls* the
   producer. This directly targets the #1 real-world failure — code that compiles
   but is never invoked. "It builds" is not "it's wired."
4. **Guardrail greps.** Assert the red lines held: e.g. the protected
   dirs/signatures are 0-diff (`git diff <path> | wc -l` is 0), no secret literal
   was added, the author signature is present on new files.

## Concrete shape

```bash
# 1) authoritative tests (the exit code that is truth)
<test-command>            # expect: all green

# 2) builds for every affected target
<build-command-a>         # expect: BUILD SUCCEEDED
<build-command-b>

# 3) wiring: the consumer really calls the producer (not just "compiles")
grep -rn "NewThing(" <consumer-files>        # expect: >= 1 real call site
grep -rn "\.newMethod(" <consumer-files>

# 4) guardrails held
git diff <protected-path> | wc -l            # expect: 0
```

Read the counts/verdicts yourself. If the grep for the new call site returns
nothing, the task is *not* done no matter how green the tests are — the code is
dead. Send it back.

## Flake vs real failure

When the authoritative command fails, decide *before* reacting: real or
environmental?

- **Real** → send to a debug subagent (one round), or `[!]` after a second failed
  round. Never "probably flaky" a red result without evidence.
- **Environmental** → confirm it's the known false-failure (isolate it: re-run the
  suite alone, away from concurrent load; re-run the specific test). Only after an
  isolated clean run do you call it a flake — and note it so it doesn't recur as a
  wrong verdict. A common trap: a resource-contention crash that only appears when
  tests run concurrently with heavy builds. Run the test command *alone* to tell.

## `[rt]` — honest runtime deferral

Some behavior can't be unit-tested: pixel layout, DOM/JS interaction, animation
feel, real-device network, on-device localization rendering. For those tasks:

- Unit-test the *logic* underneath (the string the JS will inject, the model math,
  the state transition) and prove *that* in the gate.
- Mark the task `[rt]` — built + logic-verified, visual/runtime behavior deferred
  — and record exactly what a later live pass must eyeball.

Do **not** mark such a task `[x]` and imply the live behavior is confirmed. The
`[rt]` marker is what keeps the loop's "done" honest.
