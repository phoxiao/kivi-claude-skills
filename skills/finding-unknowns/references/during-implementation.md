# During-Implementation Practices

Once work starts, unknowns stop being hypothetical. Reality contradicts the plan in small ways, constantly. The problem is that each contradiction seems too minor to record — and then three weeks later nobody can reconstruct why the code diverged from the design.

## Implementation Notes

**Targets:** unknowns that only appear on contact with reality.

**Use when:** work spans multiple sessions, multiple people, or long enough that context will be lost. Effectively mandatory for anything with review checkpoints, because a checkpoint with no record of deviations is a checkpoint reviewing fiction.

### The prompt

> "Keep an implementation-notes.md file. If you hit an edge case that forces you to deviate from the plan, pick the conservative option, log it under 'Deviations', and keep going."

### The three parts, and why each matters

**Pick the conservative option.** When reality contradicts the plan mid-flight, the choice is between stopping to ask (kills momentum, and most deviations are minor) and inventing something clever (risks compounding a wrong assumption). The conservative option — the one that's easiest to reverse, closest to existing patterns, least surprising — keeps work moving while keeping the decision cheap to revisit.

**Log it.** The log is what makes the conservative choice safe. Without it, a temporary compromise silently becomes permanent architecture.

**Keep going.** Stopping on every deviation makes the practice too expensive to sustain, and it gets abandoned. The value comes from it being nearly frictionless.

### What to log

The test: *would someone three weeks from now ask "why is it like this?"*

Worth logging:
- An assumption in the plan that turned out false
- A compromise made to work around a constraint, and what it costs
- An acceptance criterion that couldn't be checked as written, and what replaced it
- Findings from a blind spot pass or prototype that arrived after the plan was written
- A decision made under uncertainty that should be revisited with more information

Not worth logging:
- Work that went as planned — that's what the task list's checkboxes are for
- Routine debugging, or implementation detail with no downstream consequence
- Anything already written back into the plan or spec — those documents are authoritative; duplicating creates drift

### Format

Keep entries to one line so the practice stays cheap:

```
- [T7] Session TTL hardcoded in 3 places, not 1 config value → refactoring it was out of scope
      → T12 (session service) must read all three or it'll silently desync
```

What deviated → why → what it affects downstream. The third part is the one people skip and the one that pays off.

### Reviewing the log

At each checkpoint, read the whole file and assign every entry one of three outcomes:

| Outcome | Meaning |
|---|---|
| **Write back** | Affects long-term design → update the spec/plan, mark the entry archived |
| **Keep** | Still an active constraint on upcoming work |
| **Close** | Resolved or no longer relevant → mark closed with a note |

A log that only grows becomes noise nobody reads. Triage is what keeps it useful.

### Failure modes

- **Batching entries at the end of a task.** Details are already gone; you'll record what you remember, which is the least surprising subset.
- **Logging everything.** A file with fifty entries has the same information value as one with zero, because nobody reads either.
- **Never triaging.** Deviations that should have updated the plan stay buried, and the plan quietly becomes fiction.
- **Treating the log as authoritative.** It records history, not current design. Once something is written back to the spec, the spec wins.
