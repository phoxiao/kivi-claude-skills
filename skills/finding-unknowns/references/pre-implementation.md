# Pre-Implementation Practices

Five practices for surfacing unknowns *before* code exists, when changing your mind is still cheap.

**Contents**
- [Blind Spot Pass](#blind-spot-pass) — for unknown unknowns
- [Brainstorms & Prototypes](#brainstorms--prototypes) — for criteria you can only recognize
- [Interviews](#interviews) — for ambiguities you'd answer if asked
- [References](#references) — for things easier to point at than describe
- [Implementation Plans](#implementation-plans) — for decisions most likely to change

---

## Blind Spot Pass

**Targets:** unknown unknowns — the gaps you can't form a question about.

**Use when:** entering an unfamiliar codebase, subsystem, domain, or library; adopting a technique you've read about but never implemented; or any time the honest answer to "do I understand this area?" is no.

### The prompt

> "I'm working on adding a new auth provider but I know nothing about the auth modules in this codebase. Can you do a blind spot pass to help me figure out my relevant unknown unknowns and help me prompt you better."

The second clause matters as much as the first. The goal isn't only a list of risks — it's a better prompt for the actual work.

### How to run it

Search before speaking. A blind spot pass grounded in the actual codebase is worth far more than one generated from general knowledge about the topic. Read the relevant modules, trace the data flow, find the existing conventions.

Then report:

1. **What already exists** that the person didn't know about — existing abstractions, prior art in the repo, a helper that already does half the job.
2. **Constraints they'll hit** — assumptions baked into current code that the new work will violate.
3. **Decisions they'll be forced to make** that aren't in their plan yet, with the options and tradeoffs.
4. **What you're still uncertain about** after looking — this is honest and often the most valuable section.
5. **A better prompt** for the real work, incorporating the above.

### Good output vs bad output

**Bad (generic, unfalsifiable):**
> "You should be careful about session management and consider edge cases around token refresh. Security is important here."

**Good (specific, grounded, actionable):**
> "`auth/session.py` stores sessions in Redis with a hardcoded 24h TTL, set in three places rather than one config value. The provider you're adding issues 90-day refresh tokens. Nothing currently reconciles those lifetimes — you'll need to decide whether the session outlives the Redis entry or the refresh token gets truncated. Also: `middleware/auth.py:42` assumes exactly one provider and short-circuits on the first match, so adding a second provider without touching that line will silently route everything to the existing one."

The difference is that the second one could be wrong. Findings that can't be wrong aren't findings.

### Failure modes

- **Answering from general knowledge instead of the codebase.** Domain platitudes feel like insight and aren't.
- **Padding with plausible-sounding concerns.** If the area is genuinely simple, say so. Inflated passes teach the user to skim.
- **Stopping at risks.** The most useful output is often "there's already a helper for this" — the pass surfaces existing knowledge, not just danger.

---

## Brainstorms & Prototypes

**Targets:** unknown knowns — criteria you hold but have never articulated, and would recognize instantly if shown.

**Use when:** the success criterion is visual, aesthetic, spatial, or feel-based. Any time you'd say "I'll know it when I see it," text-based specification will not converge. Also use when the user has expressed a quality goal (make it friendly, clean, readable) that has no operational definition.

### The prompts

> "I want a dashboard for this data but I have no visual taste and don't know what's possible. Make me an HTML page with 4 wildly different design directions so I can react to them."

> "Before wiring anything up, make a single HTML file mocking the new editor toolbar with fake data. I want to react to the layout before you touch the real app."

### How to run it

**Make the directions genuinely different.** Four variations on the same layout with different accent colors teach nothing. Vary the underlying structure — information density, navigation model, how much is shown at once, what the primary unit on screen is. The user learns their own preferences by seeing options they'd reject.

**Use realistic content.** Lorem ipsum and placeholder numbers hide exactly the problems prototypes exist to expose — long labels, empty states, awkward text lengths, code blocks that overflow. Pull real content from the actual project.

**Match the real viewport.** A mobile-first product prototyped at desktop width has not been prototyped.

**Keep it throwaway.** A single static HTML file, outside the app, no build step, no dependencies. If it starts acquiring state management, it has stopped being a prototype.

**Capture the reasoning, not just the winner.** Why the rejected directions were rejected is durable design knowledge — it prevents relitigating the same choice later. Record it.

### What to produce afterward

Extract the reusable primitives from the chosen direction — type scale, spacing, color roles, component shapes — so implementation has something concrete to target. Otherwise the prototype gets admired and then ignored, and the built version drifts.

### Failure modes

- **Prototyping after implementation has started.** The entire value is being upstream of the expensive work.
- **Presenting one direction.** With a single option there's nothing to react against, and the user rubber-stamps it.
- **Letting the prototype become the implementation.** Prototype code is meant to be discarded; carrying it forward smuggles in throwaway decisions.

---

## Interviews

**Targets:** ambiguities you'd resolve immediately if someone asked, but that no one has asked about.

**Use when:** a request is underspecified, or when you catch yourself about to silently fill in a requirement. Especially valuable at the start of anything that will take more than a session.

### The prompt

> "Interview me one question at a time about anything ambiguous, prioritize questions where my answer would change the architecture."

Both constraints are load-bearing.

**One question at a time** — a wall of ten questions gets skimmed and half-answered. Sequential questions let each answer inform the next, and the interview can stop early when confidence is reached.

**Prioritize by architectural impact** — this is what separates a useful interview from a tedious one. Questions whose answers change the data model, the boundaries between components, or the platform are worth asking. Questions about naming, colors, or anything easily changed later are not; make a sensible default and move on.

### How to run it

Ask about what's genuinely undetermined. Before asking, check whether the answer is already available in the code, the docs, or the conversation — asking about something already stated is an obvious signal you weren't paying attention.

Ask concretely, with options and their consequences, rather than open-ended. "Should this be multi-user?" is weaker than "Multi-user from the start means auth, permissions, and sharing — roughly triples P0 scope. Single-user with multi-user-shaped data models defers all of that and stays cheap to extend later. Which?"

Stop when further questions wouldn't change what you build.

### Failure modes

- **Interviewing about things with obvious defaults.** Decision fatigue makes users stop engaging with the questions that matter.
- **Batching questions.** Defeats the sequencing benefit.
- **Asking what the codebase could answer.** Look first.

---

## References

**Targets:** known unknowns where you know what you want but describing it precisely is slow and lossy.

**Use when:** a working implementation of the behavior exists anywhere — another repo, a vendored dependency, a different language, a previous project. Also use for matching an existing codebase's conventions.

### The prompt

> "This Rust crate in vendor/rate-limiter implements the exact backoff behavior I want. Read it and reimplement the same semantics in our TypeScript API client."

### Why this beats description

Source code is unambiguous about things prose glosses over: what happens on the boundary, what the defaults are, what order operations occur in, which errors are swallowed. A paragraph describing backoff behavior will omit a dozen decisions the implementation had to make. Screenshots and docs are similarly lossy — docs describe intent, code describes behavior.

Cross-language references work well. The semantics transfer even when the idioms don't.

### How to use them

Say explicitly what should carry over and what shouldn't — semantics usually, structure sometimes, style rarely. "Same retry semantics and jitter algorithm, but use our existing `HttpClient` and our error types" is much better than "make it like this."

For conventions, point at the closest existing example in the same repo: "follow the pattern in `services/billing.py`" transmits layering, naming, error handling, and test structure in five words.

### Failure modes

- **Referencing without reading.** If you cite it, read it — a reference used as a vague gesture is worse than no reference.
- **Copying structure when only semantics were wanted.** Ask which layer transfers.
- **Stale references.** Verify the referenced code is current and actually does what it's believed to do; sometimes the reference itself is the bug.

---

## Implementation Plans

**Targets:** known unknowns — surfacing the decisions most likely to change while changing them is still free.

**Use when:** work spans more than a couple of files, or when the approach isn't obvious. The plan is for review, so it must be reviewable.

### The prompt

> "Write an implementation plan in HTML, but lead with the decisions I'm most likely to tweak with: data model changes, new type interfaces, and anything user-facing. Bury the mechanical refactoring at the bottom, I trust you on that part."

### The key idea: order by reversibility, not by execution sequence

A plan that walks through steps in the order they'll be performed buries the important decisions in the middle, where they get skimmed. Lead with what's expensive to change later:

1. **Data model and schema** — the most expensive thing to change once data exists.
2. **Interfaces and contracts between components** — expensive once multiple callers depend on them.
3. **Anything user-facing** — flows, states, what appears on screen.
4. **Mechanical work** — refactors, moves, renames. State it briefly; it doesn't need review.

The reviewer's attention is finite. Spend it where being wrong is costly.

### What makes a plan reviewable

- Concrete enough to disagree with. "Improve the data layer" can't be reviewed; a schema sketch can.
- Explicit about alternatives considered and why they lost — otherwise review turns into rediscovering the same options.
- Honest about what's still unresolved, rather than papering over gaps with confident prose.

### Failure modes

- **Plans that only restate the request.** If the plan contains no decisions, it isn't a plan.
- **Uniform detail.** Every section at the same depth means the important parts weren't identified.
- **Writing the plan after deciding.** Then it's documentation, and the review is theater.
