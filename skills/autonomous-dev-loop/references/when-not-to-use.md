# When NOT to use this loop (and what to use instead)

This method has a real cost: it's slower than alternatives because it inserts an
independent gate + independent review + a human-checkpointable pause around every
task. That cost buys trust. Spend it only when trust is what you need.

## Use something else when…

### A single task, or two or three trivial ones
Just do it inline. Spawning an implementer + gate + reviewer for a one-line fix is
pure ceremony. The loop is for *many* tasks where context rot and unreviewed
compounding are real threats. A three-task cleanup gets lighter treatment (smaller
specs, maybe a single review pass), not the full apparatus.

### One parallel fan-out with no per-item verify/review gate
If the job is "do the same independent transformation across 40 files/items" and
each result doesn't need its own build+review gate before the next proceeds, a
deterministic **workflow tool** (pipeline/parallel fan-out in one script) is the
right instrument — it's faster and purpose-built for that. The loop is for
*dependent, sequentially-verified, individually-committed* tasks where you want a
human able to look between clusters.

### Tasks are genuinely independent and you want them parallel
The loop is sequential on purpose: shared git worktree, inter-task dependencies,
clean per-task rollback. If tasks truly don't touch each other and don't depend on
each other, parallel execution (a worktree per worker) can be worth it — but that's
a different tool. Don't parallelize dependent work sharing one tree; the edits
collide.

## Why not a plain bash/`ralph`-style loop
A naive "regenerate until it builds" bash loop has no subagent isolation (so it
rots context or reruns from scratch), no independent verification (the thing that
generates also certifies), and no review. That combination is *precisely* what
produces "a pile of hollow UI that compiles and does nothing." If you find an
existing script like this in a repo, it is a warning sign, not a tool to reuse.

## Why not a headless workflow tool for *this* shape
A workflow tool that runs the whole pipeline headless in one shot is elegant and
deterministic — but it removes the two things this method exists to provide: the
orchestrator sitting *in* the loop as an independent verifier whose observed exit
codes drive commits, and the human able to interject at checkpoints. If the work
needs a person to keep a hand on the wheel (审查每个集群, catch a wrong turn before
it compounds), the workflow's "go headless to the end" property is a liability, not
a feature. Use the loop; accept that it's slower.

## The honest tradeoff table

| Situation | Tool | Why |
|-----------|------|-----|
| 1 task / a few trivial ones | inline | ceremony not worth it |
| Many dependent tasks, want verify+review+human checkpoints | **this loop** | trust > speed |
| Same independent transform over N items, no per-item gate | workflow fan-out | faster, purpose-built |
| Truly independent tasks you want parallel | workflow + per-worker worktree | avoids collisions |
| "Regenerate till green" | none — anti-pattern | no isolation/verify/review → hollow output |
