# /research — 结构化研究文档

## Description
Structured research workflows producing consistent, well-formatted documentation.

## Instructions

### Subcommands
- `/research competitive <topic>` — Competitive analysis with feature matrix and pricing
- `/research ux <url>` — UX audit using dev-browser screenshots and heuristic evaluation
- `/research tech <question>` — Technology evaluation for decision-making

### Output Location
All research documents are saved to: `docs/research/<type>-<slug>-<YYYY-MM-DD>.md`

Example: `docs/research/competitive-crm-tools-2026-03-03.md`

### `/research competitive <topic>`

#### Structure
```markdown
# Competitive Analysis: <topic>
Date: <YYYY-MM-DD>

## Executive Summary
<2-3 sentence overview of findings>

## Competitors Analyzed
1. **<Name>** — <one-line description>
2. ...

## Feature Matrix
| Feature | Competitor A | Competitor B | Competitor C | Our Product |
|---------|-------------|-------------|-------------|-------------|
| Feature 1 | ✅ | ❌ | ✅ | 🔲 Planned |
| Feature 2 | ✅ | ✅ | ❌ | ✅ |

## Pricing Comparison
| Plan | Competitor A | Competitor B | Competitor C |
|------|-------------|-------------|-------------|
| Free | ... | ... | ... |
| Pro | ... | ... | ... |
| Enterprise | ... | ... | ... |

## Key Differentiators
- <what makes each competitor unique>

## Opportunities
- <gaps we can fill>

## Recommendations
1. ...
```

#### Sources
- Use WebSearch for current pricing and features
- Cite all sources with URLs
- Note the date of information retrieval

### `/research ux <url>`

#### Workflow
1. Open URL with dev-browser
2. Take screenshots of key screens/flows
3. Evaluate against Nielsen's 10 usability heuristics
4. Document findings

#### Structure
```markdown
# UX Audit: <url>
Date: <YYYY-MM-DD>

## Overview
<site/app description and target audience>

## Heuristic Evaluation

### 1. Visibility of System Status
- Score: <1-5>
- Findings: ...
- Screenshot: <reference>

### 2. Match Between System and Real World
...

(all 10 heuristics)

## Critical Issues
1. **<Issue>** — Severity: High/Medium/Low
   - Location: <where in the UI>
   - Impact: <user impact>
   - Recommendation: <fix suggestion>

## Positive Patterns
- <what works well>

## Summary
- Overall Score: <X/50>
- Top 3 priorities for improvement
```

### `/research tech <question>`

#### Structure
```markdown
# Tech Evaluation: <question>
Date: <YYYY-MM-DD>

## Context
<why this decision matters>

## Options Evaluated
### Option A: <name>
- **Pros**: ...
- **Cons**: ...
- **Ecosystem**: community size, maintenance status, documentation quality
- **Performance**: benchmarks if available
- **Learning curve**: for our team

### Option B: <name>
...

## Comparison Matrix
| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Performance | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| DX | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Community | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Fit for us | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

## Recommendation
**<chosen option>** because <reasoning>

## Migration/Adoption Plan
1. ...

## Sources
- [Title](url)
```

### Rules
- Always include the date in the document
- Always cite sources with URLs
- Use WebSearch for current information — do not rely on training data for pricing/features
- Create the `docs/research/` directory if it doesn't exist
- Use descriptive slugs in filenames (kebab-case)
- Do NOT enter Plan Mode — research is an execution task
