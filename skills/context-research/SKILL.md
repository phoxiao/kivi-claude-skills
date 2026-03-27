---
name: context-research
description: AI research pipeline that orchestrates HF Papers API, web search, and content extraction into actionable practitioner briefings. Teaches research thinking — problem decomposition, query diversification, strategic paper reading, and cross-source synthesis. Use when the user wants to research an AI/ML topic, understand a technique, survey recent papers, find state-of-the-art approaches, or bridge academic findings to practical implementation. Triggers include "context-research", "research this AI topic", "what papers exist on", "survey recent work on", "literature review", "SOTA for", "what's the latest research on".
argument-hint: <problem> | quick <problem> | deep <problem>
---

# /context-research — AI Research Thinking Pipeline

Transform a problem statement into an actionable practitioner briefing by searching HF Papers, reading actual methodology, complementing with web findings, and synthesizing across sources.

```
problem → query expansion (5 angles) → parallel HF paper search
  → triage (relevance x recency) → deep read (methodology + results)
  → web complement (implementations, blogs, code)
  → synthesis → docs/research/context-<slug>-<YYYY-MM-DD>.md
```

## Subcommands

- `/context-research <problem>` — Full 6-phase pipeline (5 queries, top 5 papers, web complement)
- `/context-research quick <problem>` — Fast mode (3 queries, top 3 papers, skip web complement)
- `/context-research deep <problem>` — Deep mode (5 queries, top 8 papers, full web + implementation search)

## Output Location

`docs/research/context-<slug>-<YYYY-MM-DD>.md`

Example: `docs/research/context-kv-cache-compression-2026-03-23.md`

Create the `docs/research/` directory if it doesn't exist.

---

## Part 1: Research Thinking Framework

This is the core of the skill. These are cognitive strategies, not API calls. Internalize them before executing any phase.

### 1.1 Problem Decomposition — Before You Search, Map the Territory

Before generating any search query, decompose the user's problem into 5 dimensions:

| Dimension | Question | Example ("KV cache compression for long-context LLMs") |
|-----------|----------|--------------------------------------------------------|
| Core concept | What is the fundamental technique? | KV cache compression |
| Upstream | What does this build on? | Attention mechanisms, memory-efficient transformers |
| Downstream | Where is this applied? | Long-context inference, deployment cost reduction |
| Alternatives | What else solves this problem? | Sparse attention, sliding window, linear attention |
| Limitations | What are known failure modes? | Quality degradation at high compression ratios |

This map drives query expansion. Skip it and you'll search with tunnel vision.

### 1.2 Query Diversification — 5 Angles, Not 5 Rephrasings

Generate exactly 5 keyword variants. Each must surface papers the others would miss:

| Variant | Strategy | Example |
|---------|----------|---------|
| Q1 | **Exact technique** — the canonical term | "KV cache compression" |
| Q2 | **Broader category** — the parent field | "efficient transformer inference memory" |
| Q3 | **Upstream method** — the technique it builds on | "attention head pruning quantization" |
| Q4 | **Downstream application** — the use case | "long context window LLM serving deployment" |
| Q5 | **Alternative approach** — competing methods | "sparse attention linear attention mechanisms" |

**Anti-pattern**: "KV cache compression", "compressing KV caches", "KV cache size reduction", "reduce KV cache memory", "smaller KV caches" — these are rephrasings that return the same papers.

For `quick` mode: generate Q1, Q2, Q5 only (3 queries).

### 1.3 Relevance Scoring — Triage Heuristics

Score each paper 1-5 on these dimensions:

| Signal | Weight | How to assess |
|--------|--------|---------------|
| **Title match** | High | Does the title directly address the user's problem? |
| **Recency** | Medium | < 6 months = 5, 6-12 months = 4, 1-2 years = 3, older = 2 |
| **Citation/upvote signal** | Medium | HF Papers upvotes, if visible |
| **Reproducibility** | High | Links to code, models, or datasets = strong signal |
| **Methodology fit** | Varies | Method paper vs. survey vs. position paper — match to user intent |

Composite score = weighted average. Papers scoring >= 3.5 proceed to deep read.

**Exception**: A foundational paper (pre-2024) scoring 3.0 on recency but 5.0 on everything else should still proceed. Recency is a signal, not a filter.

### 1.4 Strategic Reading — Read for Extraction, Not Comprehension

Do NOT read papers linearly. Use this priority order:

1. **Abstract** (10 sec) — Is this actually relevant? Kill or proceed.
2. **Figures and tables** — Jump to results tables and architecture diagrams. Highest information density.
3. **Methodology section** — What did they change? What is the core insight? What is the algorithm?
4. **Results section** — How much improvement? On what benchmarks? Against what baselines?
5. **Ablation/Discussion** — What matters and what doesn't? What are failure modes?

**Skip**: Related Work (you already have your own survey), Introduction (redundant with abstract), Conclusion (redundant with results).

### 1.5 Practitioner Lens — Extract What Matters for Builders

For each paper, extract exactly these fields:

- **One-sentence contribution**: The single new idea, in plain language
- **Key result**: The headline number (e.g., "2.4x speedup at iso-quality on LLaMA-70B")
- **Applicability conditions**: When does this work? When does it fail? What scale/domain?
- **Implementation complexity**: Drop-in replacement | Architecture change | Training pipeline change | Requires retraining
- **Code availability**: Link to repo if it exists, or "No public implementation"

If you can't fill these fields, you haven't read deeply enough.

---

## Part 2: Pipeline Execution

### Phase 1: Problem → Query Expansion

1. Read the user's problem statement
2. Apply Problem Decomposition (Section 1.1) — write out the 5-dimension map
3. Generate 5 keyword variants using Query Diversification (Section 1.2)
4. **Print the queries to the user** before searching:

```
RESEARCH STRATEGY
Problem: <user's problem>

Decomposition:
  Core:         <...>
  Upstream:     <...>
  Downstream:   <...>
  Alternatives: <...>
  Limitations:  <...>

Search Queries:
  Q1 (exact):       <...>
  Q2 (broader):     <...>
  Q3 (upstream):    <...>
  Q4 (downstream):  <...>
  Q5 (alternative): <...>
```

### Phase 2: Parallel Search

Launch concurrent Agent sub-agents, each executing a single `paper_search` call:

```
Agent 1: paper_search(query="<Q1>", results_limit=10)
Agent 2: paper_search(query="<Q2>", results_limit=10)
Agent 3: paper_search(query="<Q3>", results_limit=10)
Agent 4: paper_search(query="<Q4>", results_limit=10)
Agent 5: paper_search(query="<Q5>", results_limit=10)
```

Each agent should return: paper title, paper ID (arxiv ID or HF paper ID), date, authors, abstract snippet, upvotes (if available), and any linked repos.

| Mode | Agents | results_limit |
|------|--------|---------------|
| quick | 3 | 5 |
| default | 5 | 10 |
| deep | 5 | 15 |

**Important**: Use the `huggingface-skills:hugging-face-paper-publisher` skill's `paper_search` via the HF MCP tool. Each sub-agent prompt should instruct it to call `paper_search` and return structured results.

### Phase 3: Triage

1. Merge all results into a single list
2. Deduplicate by paper ID / arxiv ID (keep the entry with the most metadata)
3. Apply Relevance Scoring heuristics (Section 1.3)
4. Sort by composite score descending
5. Select top N papers:

| Mode | Top N |
|------|-------|
| quick | 3 |
| default | 5 |
| deep | 8 |

6. **Print the triage table**:

```
TRIAGE RESULTS
────────────────────────────────────────────────────────────────
#  Score  Date       Code?  Title
1  4.2    2026-02    Yes    KV Cache Compression via Learned...
2  3.8    2025-11    Yes    Efficient Long-Context Inference...
3  3.7    2026-01    No     Sparse Attention for Production...
4  3.6    2025-09    Yes    Dynamic Token Pruning in...
5  3.5    2024-12    Yes    A Survey of Memory-Efficient...
────────────────────────────────────────────────────────────────
Searched: 50 papers | Unique: 32 | Selected: 5 for deep read
```

### Phase 4: Deep Read

For each selected paper:

1. **Fetch content**: Try in order:
   - `WebFetch` on `https://arxiv.org/html/<arxiv-id>` (HTML version, best for extraction)
   - If no HTML version: `defuddle parse "https://arxiv.org/abs/<arxiv-id>" -m -j` (abstract page)
   - If paper has linked HF page: `WebFetch` on `https://huggingface.co/papers/<arxiv-id>` for community context

2. **If paper links to HF models/datasets**: use `hub_repo_details(repo_ids=[<linked-repo>], include_readme=true)` to understand the implementation

3. **Apply Strategic Reading** (Section 1.4): extract methodology, key results, ablation findings

4. **Apply Practitioner Lens** (Section 1.5): fill the 5 extraction fields for each paper

5. **Do NOT summarize the abstract and call it "reading"**. You must extract information from the methodology and results sections that is NOT in the abstract.

### Phase 5: Web Complement

Skip entirely in `quick` mode.

Use WebSearch with targeted queries:

**Default mode** (3 searches):
1. `"<core technique>" blog tutorial explained` — practitioner explanations
2. `"<core technique>" github implementation` — code repos
3. `"<core technique>" production deployment experience` — real-world reports

**Deep mode** (5 searches, adds):
4. `"<core technique>" benchmark comparison evaluation` — comparative analysis
5. `"<core technique>" limitations failure cases` — known issues

For the best 2-3 web results, use `defuddle parse "<url>" -m -j` to extract clean content. Read the extracted content and pull out:
- Implementation tips not in the papers
- Known gotchas from practitioners
- Performance numbers from real deployments
- Links to working code

### Phase 6: Synthesis

Generate the output document using the template below. Save to `docs/research/context-<slug>-<YYYY-MM-DD>.md`.

**The synthesis is not a concatenation of summaries.** It must:
- Identify patterns across papers (what do multiple papers agree on?)
- Identify contradictions (where do papers disagree? why?)
- Rank approaches by practitioner applicability, not academic novelty
- Connect paper findings to web complement insights

---

## Output Document Template

```markdown
# Context Research: <Problem Statement>
Date: <YYYY-MM-DD>
Mode: <default|quick|deep>

## Executive Summary

<3-5 sentences answering: What is the current state of this problem? What is the
most promising approach right now? What should a practitioner do TODAY? This is the
only section many readers will read — make it count.>

## Key Findings

### 1. <Finding Title>
- **Paper**: <title> (<date>) [<arxiv-id>]
- **Core Insight**: <one sentence, plain language>
- **Key Result**: <headline metric with context>
- **Applicability**: <when this works / when it doesn't>
- **Complexity**: <drop-in | architecture change | retraining required>
- **Code**: [<repo-name>](<url>) | No public implementation

### 2. <Finding Title>
...

## Landscape Overview

| Approach | Paper | Date | Key Metric | Code | Complexity |
|----------|-------|------|-----------|------|------------|
| ...      | ...   | ...  | ...       | ...  | ...        |

## Methodology Deep Dive

<For the top 2-3 most relevant papers, explain the methodology in practitioner
terms. Focus on "what would I need to change in my code?" not "the authors
formulate an optimization objective." Include architecture diagrams or algorithm
steps if extracted from the paper.>

### <Paper 1 Title>

<Methodology explanation>
<Key algorithmic steps>
<Implementation considerations>

### <Paper 2 Title>
...

## Practical Implications

- **Try first**: <the lowest-risk, highest-reward approach>
- **Try if X**: <conditional recommendations based on constraints>
- **Avoid**: <approaches that look promising but have hidden costs>
- **Open questions**: <what you'd need to validate yourself>
- **Infrastructure needs**: <tooling/compute/data changes required>

## Web Complement

### Implementations Found
- [<Repo Name>](<url>) — <what it implements, stars, last updated>

### Practitioner Reports
- <Summary of real-world deployment experiences, linking to source>

### Tutorials & Explanations
- [<Title>](<url>) — <what it covers>

## Research Gaps

<What questions remain unanswered? Where is the field converging vs. diverging?
What experiments would settle open debates? What would the user need to benchmark
themselves?>

## Sources

### Papers
- [<Title>](<HF Papers URL>) — arxiv:<id> (<date>)

### Web Sources
- [<Title>](<URL>) — accessed <YYYY-MM-DD>
```

---

## Rules

- **Print strategy before searching** — the user must see the 5 queries and problem decomposition before any API call
- **Print triage table** — the user must see which papers were selected and why
- **Never summarize a paper you haven't fetched** — if WebFetch/defuddle fails, say so; do not fabricate content from training data
- **Never present paper results from training data** — always fetch live via paper_search and WebFetch
- **Always include dates** — recency is a core signal for practitioners
- **Always include code links** — this is a practitioner tool, not an academic survey
- **Always fill all 5 Practitioner Lens fields** — partial extraction means insufficient reading
- **Do NOT enter Plan Mode** — research is an execution task
- **For `quick` mode**, aim for speed — skip web complement, lighter synthesis, 3 queries only
- **Cite all sources with URLs** in the Sources section
- Use descriptive slugs in filenames (kebab-case)

## Anti-Patterns

- **Synonym queries**: searching with 5 rephrasings of the same term instead of 5 different angles
- **Abstract-only reading**: presenting paper abstracts as "findings" without reading methodology/results sections
- **Recency bias**: filtering out pre-2024 papers — foundational papers are often the most actionable
- **Academic language**: writing "the authors propose a novel framework" instead of "this tool compresses the KV cache by grouping similar keys"
- **Skipping web complement**: academic papers alone miss implementations, gotchas, and production experience
- **Information overload**: listing every paper found instead of triaging — 5 well-read papers > 30 abstracts
- **Broad web searches**: searching "machine learning" instead of `"GQA grouped query attention" github pytorch`
- **Premature synthesis**: generating the output document before completing all phases
- **Trending = relevant**: a trending paper may be irrelevant to the user's specific problem
- **Ignoring contradictions**: when two papers disagree, say so — don't pick one and hide the other
