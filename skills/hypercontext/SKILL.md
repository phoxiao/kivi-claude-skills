---
name: hypercontext
description: Spatial context awareness. Renders session state, topic maps, and traffic atlases as navigable ASCII architecture. Self-awareness as UX. Ideas as terrain.
metadata:
  version: 0.4.0
  status: documented
---

# Hypercontext — Spatial Context Awareness

You already know your own context. This skill gives you a way to show it.
Any complex topic can become a navigable map.

`/hypercontext` — session map | `/hypercontext compact` — continuation prompt | `/hypercontext map <topic>` — topic zoom map | `/hypercontext analytics` — traffic atlas

## Example

```
╔══════════════════════════════════════════════════════════════════════
║  HYPERCONTEXT — session 2026-01-29 21:30
║  ctx ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░ ~50% (100k/200k)
║  ▁▂▃▅▆▆▇▇█ velocity ─────────────────── runway: ~100k
╠══════════════════════════════════════════════════════════════════════
║
║  THREADS                               HEAT
║  ┌───────────────────┐                 ⠿⠿⠿⠿ Site deploy
║  │ Site Deploy       │                 ⠿⠿⠿⠀ SKILL refinement
║  │  ├── HTML      ✓  │                 ⠿⠿⠀⠀ DNS setup
║  │  ├── Deploy    ✓  │                 ⠿⠀⠀⠀ UX consult
║  │  └── SSL       ~  │
║  └────────┬──────────┘
║           │
║  ┌────────v──────────┐  ┌───────────────────┐
║  │ DNS Config        │  │ Skill Refinement  │
║  │  ├── CNAME     ✓  │  │  ├── Protocol  ✓  │
║  │  └── Apex      x  │  │  └── Compress  ~  │
║  └───────────────────┘  └───────────────────┘
║
║  FILES TOUCHED           TOOLS USED          SYSTEMS
║  index.html      ◆      Bash  ⠿⠿⠿⠿⠿⠿⠿⠿ 34   Win (here)  ✓
║  SKILL.md        ◆      Read  ⠿⠿⠿⠿     12   Cloudflare  ✓
║  upload-to-kv.js ◇      Edit  ⠿⠿⠿       9   Namecheap   ✓
║  worker.js       ◇      Task  ⠿⠿        5   KV Store    ✓
║                         Write ⠿         3
║
║  DECISIONS                              OPEN
║  ✓ .sh as primary domain                ? Apex TLS via CF DNS
║  ✓ Terminal-forward layout              ? OG card verification
║  ✓ KV for skill serving                 ? Compact mode testing
║
```

That's it. Render YOUR session. Introspect honestly — real threads, real files, real counts.

## How

- **Context bar**: `▓`=used `░`=remaining. 35-char bar, 200k total. Estimate: `5000 + (turns × 2000) + (files_read × 2000) + (skills × 2000)`. Round to nearest 5%.
- **Velocity**: `▁▂▃▄▅▆▇█` sparkline, left=early right=recent. One char per turn (group if >12). Ramp `▁`→`█` by activity per turn. Short early sparklines are honest.
- **Threads**: 3-6 boxes. `✓`done `~`wip `x`blocked `·`not-started `*`idea. Top blocks bottom (`│v`); side-by-side for parallel.
- **Heat**: 4-char braille fill bars ranked by recency. `⠿⠿⠿⠿`=hot `⠀⠀⠀⠀`=stale. Colored per sparkline palette (magenta→white→cyan→gray). Pure recency — no importance guessing.
- **Files**: `◆`=modified `◇`=read-only. Last 2-3 path segments, modified first.
- **Tools**: `⠿` braille bars scaled to max_count/8, round to nearest (min 1). Count after bar. Descending.
- **Systems**: `✓`=contacted this session `░`=unknown. Only relevant systems.
- **Decisions/Open**: One line each, ~35 chars max.

## Color — Unified Palette (v0.3.2)

All hypercontext modes use this ANSI color system. Emit via Node.js script or `echo -e` in Bash.

### Sparkline Levels (today column)

```
Level 0  \x1b[90m      dark gray      empty / near-zero
Level 1  \x1b[36m      dark cyan      low
Level 2  \x1b[96m      bright cyan    medium
Level 3  \x1b[1;97m    bold white     high
Level 4  \x1b[1;95m    bold magenta   PEAK / off the charts
```

Yesterday column: `\x1b[90m` (gray) — always uniform, no per-char coloring. No `\x1b[2m` dim — too dark on dark themes.

### Nova Mode

Rows with >500% day-over-day change: **all non-zero braille chars forced magenta** (`\x1b[1;95m`).
This creates a full-magenta row that screams "something happened here."

### Change Arrows

```
▼▼  \x1b[1;91m  bright red      < -50%   crash
▼   \x1b[31m    red             -50%→-20% drop
≈   \x1b[33m    yellow          ±20%      stable
▲   \x1b[32m    green           +20%→+100% rise
▲▲  \x1b[1;92m  bright green    +100%→+500% surge
★   \x1b[1;95m  bright magenta  > +500%   nova
```

### Name & Volume

```
Name rank <5     \x1b[1;97m  bold white   hot
Name rank 5-19   \x1b[0m     normal       warm
Name rank 20+    \x1b[2m     dim          cool
Volume >10K      \x1b[1;97m  bold white
Volume 1K-10K    \x1b[0m     normal
Volume <1K       \x1b[2m     dim
```

### Frame & Structure

```
Frame/borders    \x1b[36m    cyan
Title            \x1b[1;36m  bold cyan
Subtitle/legend  \x1b[90m    gray
Terminator │     \x1b[90m    gray
✓ done           \x1b[32m    green
~ wip            \x1b[33m    yellow
x blocked        \x1b[31m    red
◆ modified       \x1b[33m    yellow
◇ read-only      \x1b[90m    gray
Heat ████ hot    \x1b[1;95m  magenta
Heat ███░ warm   \x1b[1;97m  bold white
Heat ██░░ mid    \x1b[96m    bright cyan
Heat █░░░ cool   \x1b[36m    cyan
Heat ░░░░ stale  \x1b[90m    gray
Reset            \x1b[0m
```

### Rendering Notes

- Left border only. Right `║` border **deferred to v0.4** (alignment breaks with variable-width ANSI).
- **Always emit via standalone Bash calls** — ANSI color renders in terminal. Plain text in assistant messages won't show color.
- **KNOWN BUG (CC v2.1.23):** Bash output inside skill/tool context compacts at ~3 lines. Standalone `echo -e` renders fully. Workaround: emit maps as direct bash calls AFTER skill text, not nested inside it. Filed as GH issue draft in session artifacts.
- Bash heredoc + ANSI substitution is fragile. Use a temp `.js` file instead.
- Each braille char = 2 data points. Color is per-char based on `Math.max(leftLevel, rightLevel)`.
- Heat bars use braille `⠿` (full) and `⠀` (empty), colored per the sparkline level palette.

## Topic Map Mode (v0.4.0)

`/hypercontext map <topic>` — Render any complex topic as multi-zoom spatial architecture.

### What It Does

Takes a topic, concept, or question and renders it as a navigable ASCII map at 5 zoom levels:

- **Zoom 0**: Full overview — all actors, forces, relationships, verdict
- **Zoom 1-4**: Progressive deep dives into the key terrain features

### Example

```
/hypercontext map "deploy pipeline security"
```

Produces 5 maps: overview → kill chain → channel model → audit → core tension.

### How to Render

**Zoom 0 (Overview):**
- Title bar with topic + date
- All major actors/forces in labeled regions
- Arrows showing relationships (→ attacks, ← defends, ↔ tension)
- Verdict/recommendation at bottom
- ~30-40 lines

**Zoom 1-4 (Deep dives):**
- Each zooms into ONE key terrain feature from Zoom 0
- Title: `ZOOM N — THE {FEATURE NAME}`
- Quote from relevant source/advisor at top
- Detailed internal structure of that feature
- Relationships to adjacent features
- ~25-35 lines each

### Visual Language

```
Actors/regions    ┌──────────┐ └──────────┘  box-drawing
Relationships     ───→  ←───  ↔  ├──  └──    directional arrows
Status            ✓ done  ✗ gap  ~ partial  ? open  ⊕ you
Hierarchy         Ring 0 ⊃ Ring 1 ⊃ Ring 2   concentric nesting
Tension           two columns, opposing, converging at bottom
Emphasis          ██ LABEL ██  bold regions
```

### Persistence Rule (CRITICAL)

**Every map emitted MUST also be saved to a file.** Maps are too valuable to exist only in scrollback.

Pattern:
```
session_dir = mindpalace/sessions/{session-name}/
file = {session_dir}/map-{topic-slug}.md
```

Write all zoom levels to a single markdown file with `### ZOOM N` headers. Then display inline. The user gets both: immediate visibility AND persistence.

If no session directory exists yet, create one with today's date and a slug: `mindpalace/sessions/{YYYY-MM-DD}-{topic-slug}/`.

### When to Use

- Council deliberations → map the strategic terrain
- Architecture decisions → map the system topology
- Threat analysis → map the forces and vulnerabilities
- Any topic where spatial layout reveals structure prose hides

### Anti-patterns

- Don't make decorative maps. Every box, arrow, and glyph must represent real structure.
- Don't zoom into boring features. Zoom into where the tension, disagreement, or insight lives.
- Don't skip Zoom 0. The overview is the anchor — deep dives without it are disorienting.

---

## Compact Mode

`/hypercontext compact` — dense markdown for continuation-prompt.md, no ASCII boxes:

```
# Hypercontext — {date} {time}
ctx: ~{pct}% | runway: ~{remaining} | turns: {count}
## Threads — 1. {thread}: {status}
## Files — {file}: {change}
## Decided — {decision}
## Open — {question}
## Next — {action}
## Paths — {path}
```

## Analytics Mode (v0.3.2)

`/hypercontext analytics` — Render Cloudflare traffic as a braille sparkline atlas.

### What It Renders

A 48h traffic atlas across all 248 Cloudflare zones, in 4 views:

```
╔══════════════════════════════════════════════════════════════════════════════
║  SPARKLINE ATLAS — 48h braille — 2026-01-30T09:15Z — PST 01:00
║  Each char = 2 hours │ left dot = odd hour │ right dot = even hour │ 4 levels

═══ VIEW 1: BY DOMAIN (top 50) ═══════════════════════════════
                            ← yesterday (dim) →       │ ← today (bright) →
skill.cc                    ⣀⣀⣤⣤⣶⣶⣶⣤⣤⣀⣀⣀│⣀⣤⣤⣶⣶⣷⣷⣶⣤⣤⣀⣀⣀   12.3K ▲+37%
hypercontext.sh             ⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀│⣀⣀⣀⣤⣶⣷⣿⣷⣶⣤⣀⣀⣀    9.3K ★+999%

═══ VIEW 2: BY COUNTRY (top 25) ═════════════════════════════
France                      ⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀│⣀⣀⣤⣶⣷⣿⣿⣷⣶⣤⣀⣀⣀   56.5K ★+999%
United States               ⣤⣤⣶⣶⣶⣤⣤⣀⣀⣀⣤⣤│⣤⣤⣶⣶⣶⣤⣤⣀⣀⣀⣤⣤⣤   42.1K ≈+5%

═══ VIEW 3: BY TLD ═══════════════════════════════════════════
═══ VIEW 4: BY BRAND ═════════════════════════════════════════

═══════════════════════════════════════════════════════════════
48h TOTAL: 357.0K │ yesterday: 150.4K │ today: 206.6K │ +37%
═══════════════════════════════════════════════════════════════
```

### Braille Sparkline Encoding

Each Unicode braille character encodes 2 data points (consecutive hours), 4 vertical levels each:

```
LEFT_DOTS  = [0x00, 0x40, 0x44, 0x46, 0x47]   heights 0-4
RIGHT_DOTS = [0x00, 0x80, 0xA0, 0xB0, 0xB8]   heights 0-4
char = String.fromCodePoint(0x2800 | LEFT[left] | RIGHT[right])
```

- 12 braille characters = 24 hours
- Yesterday: `\x1b[90m` uniform gray (no dim — `\x1b[2m` is invisible on dark themes)
- Today: per-char coloring by peak level (gray→cyan→bright cyan→white→magenta)
- `│` terminator between 24h windows (gray `\x1b[90m`)
- Values normalized per-row: `Math.round((value / rowMax) * 4)`
- Nova mode: >500% change → all non-zero today chars forced magenta

### How to Fetch (Cloudflare GraphQL)

**API limit:** `httpRequestsAdaptiveGroups` has max 86400s (24h) time range. Split 48h into two 24h windows, fetch in parallel, merge.

**Batch pattern:** 10 zones per GraphQL query using aliases (`zone_0`, `zone_1`, ...). `zones()` returns array — use `[0]` accessor.

```
Query structure:
{ viewer {
  zone_0: zones(filter: {zoneTag: "..."}) {
    httpRequestsAdaptiveGroups(filter: {datetime_geq: "...", datetime_leq: "..."}, limit: 100) {
      count dimensions { datetimeHour }
    }
  }
  zone_1: ...
} }
```

**4 parallel streams:**
1. Yesterday zones (48h ago → 24h ago)
2. Today zones (24h ago → now)
3. Yesterday geo (same, with `clientCountryName` dimension, limit: 2000)
4. Today geo (same)

Merge: concatenate `yesterday[24] + today[24]` → `hours48[48]` per entity.

### Analytics Script

The reference implementation lives at `scripts/node/analytics-sparklines.js`.

**Future:** This will become a Rust nanotool (`cf-sparkline` / `braille-spark`) — see `infra/rust-migration-votes.md`.

### Views

| View | Groups By | Shows |
|------|-----------|-------|
| Domain | Zone ID → domain name | Top 50 by 48h total |
| Country | `clientCountryName` | Top 25 by 48h total |
| TLD | Last segment of domain | All TLDs, descending |
| Brand | First segment of domain | All brands + extensions list |

Each row: `name (26 chars)  sparkline (dim│color)  total  arrow`

Change arrows: `▼▼` crash `▼` drop `≈` stable `▲` rise `▲▲` surge `★` nova. See Color section for thresholds.

### Pattern Recognition

| Pattern | Meaning |
|---------|---------|
| Flat band across 20+ domains | Bot crawler (systematic sweep) |
| Zero yesterday, sharp ramp today | Viral event or new deploy |
| Business-hours-only activity | Regional bot (check country) |
| Uniform ~N req/domain | Scanner from CT logs |
| Sine wave, US peaks | Organic traffic |

---

## The Rule

Don't hallucinate. Every thread, file, tool count, and system status must reflect what actually happened. The map is only useful if it's true. Above ~70% → run compact for a continuation prompt.

**Persistence rule:** Any map worth rendering is worth saving. Session maps and topic maps MUST be written to `mindpalace/sessions/` alongside being displayed. Inline output vanishes on compaction. Files survive.

```
         }@{@}@{@}@{@}
       @{@}@{@}@{@}@{@}@{
      @}@{@}@{@}@{@}@{@}@{@}
     @{@}@@@@@@@@@@@@@@@@{@}@{
     @@@@@                @@@@@
     @@  ┌──────┐ ┌──────┐  @@
     @@  │  ·   │─│  ·   │  @@   "curls get claudes
     @@  └──────┘ └──────┘  @@    with skills"
      @@        /\         @@
       @\      ‾‾‾‾       /@
         `-.    ||    .-'
              `'||`'
```
