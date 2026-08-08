# Subagent prompt templates

These two prompts are the highest-leverage artifacts in the whole method. A vague
implementer prompt produces vague work you then have to fix; a vague review prompt
produces "looks good" that catches nothing. Invest in them.

The orchestrator does the *scouting* (reads the real files, finds the exact call
sites and signatures) and bakes those specifics into the prompt, so the fresh
subagent doesn't burn context rediscovering them and doesn't guess wrong.

---

## Implementer prompt template

Spawn as a **background** subagent with a fresh, general-purpose context. Fill
every bracket with specifics *you already looked up* — file paths, line numbers,
exact signatures, the real red lines.

```
You are implementing ONE task in <project> at <repo path>, branch <branch>.
Work test-first where the seam allows. Return a COMPACT structured report —
your final message is DATA for the orchestrator, not prose for a human.

## Task <id> — <one-line goal>

### The problem (why this task exists)
<2-4 sentences: what's broken/missing and the user-visible consequence. Give the
subagent the "why" so it can make good local judgment calls, not just follow steps.>

### Current state (what to read — with exact locations)
- <file:line> — <what's there now and why it's wrong/insufficient>
- <the reference implementation to mirror, if one exists: file:line>
- <the seam/signature it must fit>

### Required behavior
1. <precise, verifiable change #1>
2. <#2 — include the tricky edge cases you already know about>

### Constraints (HARD — violate any → stop and report BLOCKED, don't work around)
- Do NOT change <protected signatures/dirs> — `git diff <path>` must stay empty.
- <other red lines: no secrets in logs, author signature = ..., localize strings, etc.>
- Keep changes additive/minimal; if a real design gap forces a bigger change, report it, don't silently make it.

### Tests (put the weight where the seam is clean; RED first)
- Write a failing test proving <the core behavior>, confirm it's RED, then implement to GREEN.
- <the specific assertion that proves the payoff — e.g. "search finds the book by
  its NEW name and NOT the old" — make the assertion load-bearing, not a tautology>
- Run <authoritative test command> → expect <current count> + your new ones, all green.
- Build <every affected target> → all succeed.
- If it's runtime-only (visual/DOM/device), unit-test the underlying logic and say so honestly ([rt]).

### Report back (compact, structured)
- Files changed/added (path — one-line what).
- The approach in 2-3 lines (esp. any non-obvious decision).
- Test names + what they assert + RED evidence + final test count.
- Build results.
- Confirm the hard constraints held (the 0-diff greps).
- Any deviation from this spec, or anything that needs an orchestrator decision.
```

Why the shape works: the "why" enables judgment; the exact locations save context
and prevent wrong guesses; "HARD constraints → report BLOCKED, don't work around"
stops a subagent from cleverly violating a red line to make its task pass; "RED
first + a load-bearing assertion" stops tests that pass without proving anything;
the compact structured report keeps the orchestrator's context lean.

---

## Code-reviewer prompt template

Spawn as a **background** subagent, fresh context, ideally a code-reviewer agent
type. It must NOT have seen the implementation reasoning — that independence is
the whole value. Point it at *this task's diff only*.

```
Review ONE uncommitted diff in <project> at <repo path> (branch <branch>).
Run `git diff` (and read any new untracked files); review ONLY the changed code.

## What the change does (task <id>)
<3-5 sentence summary of intent + approach, so the reviewer knows what "correct"
means here without reading the implementer's rationalizations.>

## Review priorities (rank the real risks for THIS change)
1. <the sharpest correctness risk — e.g. "does X still hold when input is empty /
   the save fails / two of these run concurrently?"> Give a concrete verdict.
2. <the wiring/observation/lifecycle risk specific to this stack>
3. <the guardrail/red-line check: protected dirs 0-diff, no secret, signatures unchanged>
4. <tests meaningful? RED credible? or do they pass without proving the behavior?>

## Output
- Verdict: CLEAN, or findings as (file:line, concrete failure scenario, severity blocker/should-fix/nit).
- DIRECT call on <the 1-2 subtle risks you most want an answer on>.
- Concise. Do NOT fix — just report. Treat runtime-only behavior as [rt] (reason from code; don't demand a unit test for pixels). Ignore pre-existing issues outside the diff.
```

Why the shape works: giving the reviewer the *intent* but not the *rationalization*
lets it judge against the goal with fresh eyes; ranking the real risks focuses it
(an unfocused reviewer rubber-stamps); "concrete failure scenario + severity" makes
findings actionable and triageable; "DIRECT call on the subtle risks" forces a
verdict on the things you're actually unsure about instead of a vague survey;
"don't fix, just report" keeps the reviewer independent and the fix decision yours.

## Handling review findings

- **blocker / should-fix** that's clearly right and small → fix it yourself in one
  tight edit (you have the context), re-run the gate, then commit. Faithfully apply
  the reviewer's actual suggestion; don't half-fix.
- **finding you disagree with** → say why, in the commit/queue note. The reviewer is
  advisory, not infallible; but "I disagree" needs a reason, not a shrug.
- **finding that reveals an Ask-first-sized issue** (a security-sensitive design, a
  needed signature change) → `[!]`, stop, surface to the user.
- **nits** → apply if cheap, otherwise note and move on.
