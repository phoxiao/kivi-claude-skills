# The queue anchor file

The queue is the loop's single source of truth and its program counter. Put it
in the repo (e.g. `specs/tasks/loop-queue.md` or `docs/loop-queue.md`) so it is
versioned alongside the work. Everything the orchestrator needs to resume after a
context reset lives here + in `git log`.

## What each part is for

- **Header** — the resume instructions, the authoritative verification command,
  the source-of-work references, and the hard guardrails / Ask-first gates. This
  survives a context reset, so a re-woken orchestrator re-derives the rules from
  the file, not from memory.
- **Per-task lines** — one line per task with a status marker, a short imperative
  spec, and (once done) the commit hash + a one-line result (tests added, review
  verdict, any deferral). Group tasks into clusters when there are dependencies or
  natural checkpoint boundaries; order so pure-logic/foundational tasks precede
  the UI/wiring tasks that depend on them.
- **Progress line** — a single glanceable line (e.g. `12 / 21 · cluster A ✅ · B
  3/7`). Keep it accurate; a stale progress line is worse than none.

## Status markers

| Marker | Meaning |
|--------|---------|
| `[ ]` | todo |
| `[~]` | in progress (rarely needed; the loop does one task at a time) |
| `[x]` | done — **must carry the commit hash** |
| `[!]` | blocked — **must carry the reason** (verification stuck after 2 rounds, or an Ask-first gate hit) |
| `[rt]` | code builds + unit tests green, but the real payoff is visual/DOM/timing/device behavior a unit test can't reach. Honestly deferred to a runtime pass — **not** a silent "done". |

`[rt]` matters because it keeps you honest: don't claim a live behavior works when
you only proved the logic underneath it. List every `[rt]` so a later runtime pass
knows exactly what to eyeball.

## Copyable template

```markdown
# <Project> Loop Queue

> **Single source of truth.** After a context reset: re-read this file + `git log --oneline` to resume exactly.
> Status: `[ ]` todo · `[~]` doing · `[x]` done(+commit) · `[!]` BLOCKED(+reason) · `[rt]` builds+unit-green, runtime-verify later
> Authoritative verification = `<the one command whose exit code is truth>` (note any known false-failures)
> Source of work: <audit / spec / backlog links>

## Per-task lifecycle (orchestrator runs this)
1. Implement subagent (fresh ctx): read spec + files → RED→GREEN, self test+build, compact receipt
2. Verification gate (I run it independently): authoritative test + build(s) + wiring grep → not green: 1 debug round, then `[!]`
3. Review subagent (fresh ctx, code-reviewer): this task's diff vs red lines → findings: fix or `[!]`
4. Pass → commit + tick this file with the hash
5. Every few tasks / cluster boundary → checkpoint summary

## Hard guardrails (hit one → stop and ask; never proceed on assumption)
- <e.g. no public-signature changes that break tests>
- <e.g. no default network egress / no sending user data to third parties>
- <e.g. no secrets in plaintext or logs; author signature = ...>
- Ask-first gates: <new external dependency, schema/data-model change, any irreversible action>

---

### Cluster A — <theme> (do first: foundational / pure-logic)
- [ ] **1. <task id>** <one-line imperative spec> · verify: <what proves it>
- [ ] **2. <task id>** <spec> · verify: <...>

### Cluster B — <theme>
- [ ] **3. <task id>** <spec> · verify: <...>

---

## Progress
`0 / N` · A 0/2 · B 0/1
```

## Filled-in example line (after a task lands)

```markdown
- [x] **3. cover-cache** Wire the 3-tier cover cache: import calls generateThumbnail;
  cards use shared getCover(downsample) · `e3ff836` · 3 tests (self-heal / nil / downsample) ·
  review APPROVE (fixed a test that didn't actually prove downsample)
```

Note how the finished line records the *commit*, the *tests*, and the *review
outcome including what it caught*. That density is what lets a future reader (or a
re-woken you) trust the line without re-deriving it.

## Resume protocol (the reliability guarantee)

If the conversation is summarized or dies at task K:

1. `cat <queue-file>` → the first `[ ]` (or `[~]`) is where to resume; everything
   above it is `[x]`/`[!]`.
2. `git log --oneline` → confirm each `[x]` line's commit hash actually exists and
   the working tree is clean (no half-finished task). If a task is marked `[x]`
   but has no commit, or the tree is dirty, reconcile before continuing.
3. Resume from the first `[ ]`.

Recovery relies on **zero** memory of what you did — only the file and git. That
is the entire point of externalizing state.
