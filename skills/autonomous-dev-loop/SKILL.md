---
name: autonomous-dev-loop
description: >-
  Run a long list of implementation/remediation tasks as a resumable autonomous
  loop where each task is built by a fresh-context subagent, verified by the
  orchestrator itself (not the implementer), and reviewed by an independent
  code-reviewer subagent before commit. Use this WHENEVER the user wants to work
  through many tasks in a loop, batch-fix an audit/backlog/checklist, "run a
  loop" over a task list, do autonomous or unattended multi-task development, or
  grind through a remediation plan — even if they don't say the word "loop".
  Also use it when a single long session keeps losing context across many tasks,
  when hollow "it compiles so it's wired" verification keeps slipping bugs
  through, or when autonomous work green-lights everything without review. Not
  for a single one-off task (just do that directly) or for orchestrating one
  parallel fan-out with no per-task verify/review gate (use a workflow tool).
---

# Autonomous Dev Loop

A method for completing **many** implementation tasks in sequence, autonomously,
without (a) rotting the orchestrator's context, (b) shipping unverified work, or
(c) green-lighting everything unreviewed. It is not an unattended bash loop — it
is a multi-agent pattern: **thin orchestrator, throwaway workers, memory in
files, verification run by the judge not the athlete, review from an independent
set of eyes.**

## The one-sentence mental model

> **git commits are persistent storage. The queue file is the program counter.
> A background subagent finishing is the clock tick. The orchestrator (you, the
> main conversation) is the unit that runs verify → review → commit → spawn-next
> on each tick.** The loop self-perpetuates by spawning the next background
> worker at the end of each turn, and stops simply by *not* spawning one.

Anti-context-rot does **not** come from the loop mechanism. It comes from
**subagent isolation + state living in files/git.**

## Why this shape (read this — it's the whole point)

Doing N tasks naively fails three ways, and each piece below answers one:

1. **Context rot.** Twenty tasks in one conversation and context blows by task
   ~8: summarization drops early decisions, `file:line` references go stale, you
   re-read files, quality slides. → *Fix: each task is built by a fresh,
   disposable subagent; the orchestrator keeps only a compact receipt.*
2. **Sham verification.** The most common defect in real audits is "the service
   was written, assumed wired, but the UI never calls it." An implementer that
   verifies its own work cannot catch this — its context is full of "why I wrote
   it this way" rationalizations. → *Fix: the orchestrator runs verification
   itself, independently, including a wiring check — not just "does it compile."*
3. **Rubber-stamping.** Autonomous loops love to run all-green off a cliff,
   compounding small issues. → *Fix: an independent code-reviewer subagent (fresh
   context, not polluted by the implementation narrative) reviews each diff.*

## The division-of-labor principle (the load-bearing idea)

Decide where each piece of work runs by two questions:

- **Deterministic command whose result must drive the commit/rollback decision?**
  → **run it in the main loop yourself** (the verification gate). A receipt that
  says "tests pass" is a *claim*, not a fact; the authoritative exit code must
  enter *your* context to be trusted. Spawning a subagent for `test`/`build`/`grep`
  is pure overhead (startup cost + logs summarized through another context, losing
  fidelity).
- **Judgment work that benefits from an independent perspective?** → **subagent**
  (implementation, code review, and — only when verification fails for an unclear
  reason — failure diagnosis).

Athlete ≠ referee. The implementer wrote the code; it is the wrong agent to
certify it.

## Per-task lifecycle (the control flow)

For each `[ ]` task in the queue, in order:

1. **Implement (fresh-context subagent).** Hand it a *precise* spec: the exact
   files, the acceptance criteria, the constraints/guardrails, and how to verify
   itself. Have it work test-first where the seam allows (write the failing test,
   then the minimal implementation), self-run tests+build, and return a **compact
   structured receipt** — not prose. See `references/subagent-prompts.md` for the
   implementer prompt template.
2. **Verification gate (you run it, independently).** Do not trust the receipt.
   Run the authoritative test command + build(s) + the wiring grep yourself.
   Green → proceed. Not green → spawn one debug subagent; still not green after a
   second round → mark the task `[!]` with a diagnosis and move on (don't grind
   forever). See `references/verification-gate.md`.
3. **Review (independent code-reviewer subagent, fresh context).** Point it at
   *this task's diff* and the project's red lines. It returns CLEAN or concrete
   findings (file:line, failure scenario, severity). Findings → fix in one round,
   or escalate to `[!]`. Reviews earn their keep: across a real run they routinely
   catch bugs the gate can't — off-by-one dedup, orphaned state on failure, a
   filter stuck on a phantom id, a NaN divisor. See `references/subagent-prompts.md`.
4. **Commit + tick the queue.** Commit with a descriptive message; then update the
   queue line to `[x]` (or `[rt]`, see below) **with the commit hash**. The commit
   and the tick are how the loop remembers it's done.
5. **Checkpoint at boundaries.** Every few tasks, or at a cluster boundary,
   summarize for the human. See Checkpoints below.

Continue until the queue is empty, a task hits `[!]`, or you hit an Ask-first
gate — then stop and report.

## The engine: event-driven self-invocation

A turn ends when you stop making tool calls. So what re-wakes the orchestrator
for the next step? **Spawn the implementer/reviewer as a *background* subagent
and yield the turn; when it finishes, the harness re-wakes you automatically via
its completion notification.** No timer polling — the "real work finished" event
*is* the clock. The chain continues because each turn ends by spawning the next
background worker; it stops the moment a turn ends without spawning one. That is
literally how "self-paced" and "hard-stop at checkpoint" are implemented:
**stopping = not spawning next this turn.**

(Use a long fallback timer only as a heartbeat in case a subagent hangs and never
returns — not to poll for work the harness already notifies you about.)

Three facts to keep straight:
- **Re-waking ≠ context reset.** The harness re-wakes the *same* conversation
  (which may get summarized), not a clean context. Cleanliness comes from the
  subagents + the files, not from re-waking.
- **The program counter is the queue file, not your memory.** On every wake, the
  first move is to *read the queue* to learn which task is next — never rely on
  "I remember I just finished N."
- **Sequential, not parallel.** The tasks share one git worktree and often depend
  on each other; parallel edits collide. (Parallel would require a separate
  worktree per subagent — over-engineering for dependent, sequentially-verified
  work. Reach for it only when tasks are truly independent.)

## The queue file (single source of truth)

One markdown file is the anchor. It holds every task with a status marker, a
one-line spec, and — once done — the commit hash and a one-line result. Status
markers: `[ ]` todo · `[~]` in progress · `[x]` done (with commit) · `[!]`
blocked (with reason) · `[rt]` builds+unit-tested green, but visual/DOM/runtime
behavior can only be confirmed live — deferred honestly, not silently.

This file is what makes the loop **resumable**: if the conversation is summarized
or dies mid-loop, you recover with zero reliance on memory —

1. read the queue file → see which tasks are `[x]` and which is the next `[ ]`;
2. `git log --oneline` → confirm each `[x]`'s commit exists and there's no
   half-finished dirty state;
3. resume from the next `[ ]`.

See `references/queue-anchor.md` for the exact format and a copyable template.

## Checkpoints: hard-stop vs soft-stop (ask the user which)

At each checkpoint (every few tasks / cluster boundary), you either:
- **Hard-stop (safer default):** summarize and *wait* for the user; do nothing
  until they say continue. Best when they want to eyeball every cluster.
- **Soft-stop:** emit the summary + a resumable marker, then *auto-continue* the
  next cluster. Best for an unattended full run, reviewed in batch afterward.

Recommend hard-stopping the first cluster so the user calibrates trust on real
output, then switching to soft-stop for the rest. **Two rules hold regardless of
mode:** an Ask-first gate always hard-stops (even in soft mode), and two failed
fix rounds → mark `[!]` and skip (never grind indefinitely).

## Guardrails and Ask-first gates

Before starting, agree with the user on the **hard guardrails** (things the loop
must never do autonomously) and the **Ask-first gates** (decisions it must stop
and ask about rather than guessing). Typical examples: changing a public API
signature that breaks existing tests, introducing default network egress or
sending user data to third parties, storing secrets in plaintext/logs,
schema/data-model changes, or any irreversible/security-sensitive action. When
the loop hits one, it marks `[!]` and stops — it does not proceed on assumption.
Encode these in the queue file's header so they survive a context reset.

## Honesty rules (do not fake progress)

- If verification fails, say so with the output. If a step was skipped, say so.
- Distinguish a **real failure** from an **environmental flake** (e.g. a test that
  fails only under concurrent load, a simulator-Keychain error). Pick one
  authoritative command as the source of truth and note known false-failures so
  they don't cause a wrong verdict — but never wave away a real regression as
  "probably flaky" without evidence (e.g. isolated re-runs).
- Mark runtime-only verification `[rt]` honestly rather than claiming a visual/DOM
  behavior is confirmed when only the underlying logic is unit-tested.

## Scaling the rigor to the request

"Fix these few things" → lighter: smaller specs, single-pass review. "Thoroughly
work through this whole audit / be comprehensive" → full rigor: precise specs,
independent gate + independent review every task, checkpoints, `[rt]` honesty.
Don't impose the whole ceremony on a three-task cleanup, and don't run a
forty-task audit on vibes.

## Reference files

- `references/queue-anchor.md` — queue file format, status markers, resume protocol, copyable template.
- `references/verification-gate.md` — how to run the independent gate: authoritative command, the wiring grep that targets hollow-wiring, flake-vs-real, `[rt]`.
- `references/subagent-prompts.md` — copyable prompt templates for the implementer subagent and the code-reviewer subagent (the two highest-leverage artifacts).
- `references/when-not-to-use.md` — when a plain workflow tool or just-do-it-inline is the better call, and the tradeoffs.
