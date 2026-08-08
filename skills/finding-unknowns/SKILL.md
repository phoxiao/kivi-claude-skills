---
name: finding-unknowns
description: Surface unknown unknowns before they turn into expensive rework — blind spot passes, throwaway visual prototypes, one-question-at-a-time interviews, reference implementations, decision-first plans, implementation notes, and comprehension quizzes. Use this whenever work is about to begin in an unfamiliar codebase or domain, before committing to an implementation plan or spec, when a plan exists but has not been stress-tested, when requirements feel vague or suspiciously "obvious", when success criteria are visual and can only be recognized rather than described, when picking up work after a context gap, or when a change is about to merge and nobody has verified they actually understand it. Trigger on phrases like "find my unknowns", "blind spot pass", "what am I missing", "stress-test this plan", "I don't know this part of the codebase", "before I start building", "review my plan", "is this plan solid", "am I forgetting anything".
---

# Finding Your Unknowns

## Why this matters

You cannot ask for what you don't know you're missing.

Most expensive rework doesn't come from bad execution — it comes from a plan that was confidently built on an assumption nobody examined. The plan looked complete because the gaps were invisible. By the time reality contradicts it, code exists, decisions have calcified, and fixing it costs ten times what a question would have cost.

The practices here are each a cheap mechanism for pulling information out of a blind spot and into the prompt *before* it becomes expensive. As the source article puts it: reducing and planning for your unknowns **is** the skill of agentic coding.

The economics are the whole argument. A blind spot pass costs an hour. Discovering the same thing after three days of building costs three days.

## The four quadrants

Every gap between the plan and reality sits in one of four places. Knowing which one you're facing tells you which practice to reach for — they are not interchangeable.

| Quadrant | What it is | Why it hurts | Practice |
|---|---|---|---|
| **Known knowns** | What you already put in the prompt | — | (nothing needed) |
| **Known unknowns** | Gaps you're aware of but haven't resolved | You know to ask, but describing precisely is slow and lossy | **References**, **Implementation plans** |
| **Unknown knowns** | Things so obvious to you that you never articulated them — but you'd recognize them instantly if shown | Claude can't read your taste or your team's unwritten conventions | **Prototypes**, **Interviews** |
| **Unknown unknowns** | What you haven't considered, or don't know exists | The dangerous one — you can't even form the question | **Blind spot pass** |

Two more categories emerge once work is underway:

| Situation | Practice |
|---|---|
| Reality contradicts the plan mid-flight | **Implementation notes** |
| You shipped it but can't explain it | **Quizzes**, **Pitches & explainers** |

## Diagnosing which practice to use

Start from the situation, not the practice list.

**"I'm about to touch code I don't understand."**
→ **Blind spot pass.** This is the flagship. Unfamiliar subsystem, new domain, unfamiliar library, someone else's architecture.

**"I know roughly what I want but describing it is painful."**
→ **References.** If a working implementation exists anywhere — another repo, a vendored crate, a different language — point at it. Source code carries far more precision than prose or screenshots.

**"I'll know it when I see it."**
→ **Prototypes.** Any criterion that is visual, aesthetic, or feel-based cannot be converged on in text. Stop writing specs and generate several throwaway directions to react to.

**"The requirements feel vague but I can't say why."**
→ **Interviews.** Have Claude extract the ambiguities from you, one question at a time, prioritized by architectural impact.

**"I have a plan and I'm about to start building."**
→ **Implementation plan, decision-first.** Lead with what's most likely to change; bury the mechanical parts.

**"I'm mid-implementation and reality just contradicted the plan."**
→ **Implementation notes.** Log the deviation, take the conservative option, keep moving.

**"This is about to merge and I'm not sure I actually understand it."**
→ **Quiz yourself.** Especially for code you'll maintain long-term.

**"I need someone else to approve or adopt this."**
→ **Pitch/explainer.** Package the artifacts you already produced.

## Smells that you have unaddressed unknowns

Reach for a practice when you notice any of these — they're reliable signals, and they're easy to talk yourself out of:

- A plan step is described in one clause but would take a day to build ("...and generate the review cards"). **Single clauses hide the hardest problems.**
- An acceptance criterion can't actually be checked ("output matches the source" when the source doesn't contain that thing).
- You're about to build something whose quality is visual, but no one has defined what good looks like.
- A risk was noted and the mitigation is "write more tests." Tests verify *known* unknowns; they cannot discover unknown ones.
- The plan says "obviously" or "simply," or you catch yourself thinking a step is trivial.
- A number is required (a budget, a threshold, a duration) and no one has said where it comes from.
- You're picking work back up after a gap and reconstructing intent from memory.

## Working the practices

Read the reference file for the phase you're in — each contains the concrete prompts, what good output looks like, and the failure modes:

- **`references/pre-implementation.md`** — Blind spot pass, prototypes, interviews, references, implementation plans. Read this before committing to a plan.
- **`references/during-implementation.md`** — Implementation notes. Read when work is underway.
- **`references/post-implementation.md`** — Quizzes, pitches and explainers. Read when a change is ready to merge or share.

## How to run this well

**Do the exploration, don't just recommend it.** If you identify that a blind spot pass is warranted, run it — search the codebase, name the specific unknowns, report what you found. A list of practices the user *could* do is worth much less than the unknowns you actually surfaced.

**Name specific unknowns, not categories.** "There may be edge cases around auth" is not a finding. "Sessions are stored in Redis with a 24h TTL, but the new provider issues 90-day refresh tokens — nothing currently reconciles those lifetimes" is a finding. Specificity is what makes an unknown actionable.

**Surface disagreements with the plan.** If the existing plan, spec, or the user's stated assumption looks wrong, say so plainly and explain why. Discovering that the plan is wrong is the point of the exercise — softening it defeats the purpose.

**Report honestly when you find nothing.** A blind spot pass that turns up little is a real result and worth stating plainly. Manufacturing concerns to look thorough wastes the user's attention and trains them to ignore future passes.

**Prefer cheap and throwaway.** Prototypes should be single static HTML files, not branches. Blind spot passes produce notes, not refactors. The value is in the information, and anything that starts to feel like real implementation has stopped being exploration.

**Mind the specificity tradeoff.** Over-specify and Claude follows instructions past the point where a pivot would be better; under-specify and it fills gaps with generic best practices that may not fit. Practices like interviews and prototypes exist precisely to find the right altitude before committing.

## If the project uses spec-driven artifacts

When a repo already keeps planning documents (`SPEC.md`, `PLAN.md`, `TASKS.md`, or similar), write findings back into them rather than leaving them in chat — chat is lost, documents survive context boundaries:

- Blind spot pass results and prototype decisions → a task or section in the plan, so they gate the work that depends on them.
- Deviations found mid-flight → an implementation notes file, reviewed at each checkpoint.
- Anything that invalidates a stated assumption → fix the source document, don't just note the contradiction.

If no such artifacts exist, don't create ceremony for its own sake. A short summary in the conversation is often the right size.
