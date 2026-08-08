# Post-Implementation Practices

Two unknowns survive shipping: *do you actually understand what was built*, and *does anyone else*.

Both get skipped because the work appears finished. But code you can't explain is code you can't maintain, and work nobody understands doesn't get adopted.

---

## Quizzes

**Targets:** the gap between "the tests pass" and "I understand this."

**Use when:** you'll maintain this code long-term, the change was substantial or in unfamiliar territory, most of it was agent-written, or you're about to approve something you only skimmed. Especially valuable before merging work in a subsystem you'll be debugging at 2am later.

### The prompt

> "I want to make sure I understand everything that's happened in this change. Give me a HTML report on the changes for me to read and understand with context, intuition, what was done, etc. and a quiz at the bottom on the changes that I must pass."

### Why a quiz rather than a summary

Reading a summary produces the feeling of understanding without the fact of it — the explanation is right there, so nothing is being retrieved. A question you have to answer from memory exposes what you actually absorbed. This is the testing effect, and it's the same reason the practice appears in learning systems.

"That I must pass" is a real constraint, not a flourish. Failing a question is the signal — it identifies exactly which part to re-read.

### What makes a good quiz here

**Explanation first, then questions.** The report should build genuine intuition — why this approach, what alternatives were rejected, where the tricky parts are — before testing.

**Ask about consequences, not trivia.** Weak: "what is the function on line 40 called?" Strong: "if the upstream service starts returning 429s, what happens to queued jobs, and where would you look first?" Good questions target the reasoning you'd need during an incident.

**Cover the parts most likely to break.** Error paths, concurrency, assumptions that could be invalidated, anything the implementation notes flagged as a compromise.

**Include at least one question about a deliberate tradeoff.** If the answer is "we chose X over Y because Z," the reader should be able to reconstruct Z.

### Failure modes

- **Questions answerable from the surrounding text.** Tests reading comprehension, not understanding.
- **Trivia about names and line numbers.** Not the knowledge that matters later.
- **Skipping it because tests pass.** Tests verify the code works; the quiz verifies *you* work.

---

## Pitches & Explainers

**Targets:** other people's unknowns about your work.

**Use when:** you need buy-in, review, adoption, or a handoff. Also useful as a forcing function for yourself — if it can't be explained clearly, it may not be understood clearly.

### The prompt

> "Package the prototype, the spec, and the implementation notes into a single doc I can drop in Slack to get buy-in. Lead with the demo GIF."

### The key idea: package artifacts you already have

The practices upstream produced exactly the material a pitch needs — prototypes show what it looks like, the spec shows what problem it solves, implementation notes show what was learned. The pitch is assembly, not new writing. If those artifacts exist, this is cheap; if they don't, that's a signal the earlier practices were skipped.

### Structure

**Lead with the demo.** A GIF, screenshot, or prototype link. People decide whether to keep reading in about five seconds, and nothing earns that attention like seeing the thing work.

**Then the problem**, in the reader's terms — what was painful before.

**Then what changed**, briefly.

**Then what it cost and what's still open.** Honest limitations build more trust than a flawless pitch, and they preempt the objections that would otherwise arrive as pushback.

**Then the ask.** Be explicit: approval, review, someone to try it. A pitch with no ask gets a thumbs-up emoji and no action.

### Adjust for the reader

Someone approving a decision needs tradeoffs and cost. Someone adopting a tool needs how to start. Someone inheriting the code needs architecture and gotchas. Same artifacts, different emphasis — write for the specific reader rather than producing one generic document.

### Failure modes

- **Leading with implementation detail.** The reader hasn't been convinced they should care yet.
- **Hiding limitations.** They surface during review anyway, and having concealed them costs credibility.
- **Writing it from scratch.** If you're not assembling existing artifacts, check whether the upstream practices were skipped — that's the real finding.
