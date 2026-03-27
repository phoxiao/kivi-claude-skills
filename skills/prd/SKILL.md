---
name: prd
description: Generate structured PRD documents optimized for code agent consumption. Use this skill when the user wants to create a PRD, write product requirements, define a product spec, plan a new product or feature, convert rough ideas or meeting notes into structured requirements, or prepare specifications for task decomposition. Trigger on mentions of PRD, product requirements, product spec, feature spec, requirements document, or when the user describes a product idea and needs it formalized. Works with /task-list for seamless idea-to-implementation pipeline.
argument-hint: [source-file-path]
---

# /prd -- Structured PRD Generation

Generate a developer-ready PRD (Product Requirements Document) optimized for code agent consumption. The output integrates seamlessly with `/task-list` for task decomposition.

## Pipeline

```
idea or file --> /prd --> specs/prd.md --> /task-list --> implementation
```

## Instructions

### Determine Mode

- `/prd` (no argument): From-scratch mode. Ask the user for a brief product description to bootstrap.
- `/prd <file-path>`: File mode. Read the source file and extract structured information.

Both modes follow the same workflow below.

---

## Workflow

### Step 1: Bootstrap Draft PRD

**From scratch** (`/prd`):
1. Use AskUserQuestion to ask:
   - "Describe what you want to build in 1-2 sentences"
   - Include options for common product types (Web App, Mobile App, API/Backend, CLI Tool, Browser Extension, Library/SDK) to help set context
2. From the response, generate a skeleton PRD using the template below
3. Fill in what you can infer; mark unknowns as `[TBD]`

**From file** (`/prd <file-path>`):
1. Read the source file(s) with the Read tool
2. Extract all available structured information: features, users, tech stack, constraints, data models, APIs
3. Restructure into the PRD template below
4. Fill sections from the source material; mark gaps as `[TBD]`

### Step 2: Write Draft

Write the draft PRD to `specs/prd.md` (create `specs/` directory if needed).

This draft serves as the input for the interview phase. Having a concrete document makes the interview more productive — the user can react to specific sections rather than answering abstract questions.

### Step 3: Interview

Invoke the `/interview` command on the draft PRD:

```
/interview specs/prd.md
```

The interview command will:
- Use AskUserQuestion to deeply probe technical implementation, UI/UX, concerns, and tradeoffs
- Focus on `[TBD]` sections that need filling
- Write refined content back to `specs/prd.md`

This is the core requirements-gathering phase. Let the interview run until the user and interviewer are satisfied.

### Step 4: Post-Interview Validation

After the interview completes, read `specs/prd.md` and validate:

1. **Completeness check**: Scan for remaining `[TBD]` markers. If critical sections (MVP Scope, Data Models, or Development Phases) still have `[TBD]`, ask the user to fill them with one more targeted AskUserQuestion round.

2. **task-list compatibility check**:
   - Section 2 (MVP Scope) has explicit in-scope and out-of-scope lists
   - Section 5 (Feature Specs) uses P0-P3 priority labels
   - Section 6 (Data Models) has concrete entity definitions with field names and types
   - Section 9 (Development Phases) uses "Phase N: Name" format with clear scope per phase

3. **Structural check**:
   - All 10 sections present (some may be marked N/A for simple projects)
   - Code blocks used for data models, API schemas, flow diagrams
   - Tables used for feature lists with priorities
   - No wall-of-text prose — structured formats throughout

Fix any issues found during validation by editing `specs/prd.md`.

### Step 5: Finalize

1. Remove any remaining `[TBD]` placeholders (replace with "N/A" or remove the section if truly not applicable)
2. Output a terminal summary:

```
================================================================
  PRD Generated -- {Product Name}
================================================================

  Sections:  10/10 complete
  Features:  {N} features defined ({P0 count} P0, {P1 count} P1)
  Phases:    {N} development phases
  Models:    {N} data entities

  Output:    specs/prd.md
  Next:      /task-list specs/prd.md
================================================================
```

3. Suggest running `/task-list specs/prd.md` as the next step

---

## PRD Template

The PRD follows this structure. Each section is designed for machine parseability — prefer tables, code blocks, and explicit lists over narrative prose.

### Section 1: Overview

```markdown
## 1. Overview

**Product**: {name}
**One-liner**: {what it does in one sentence}
**Problem**: {what pain point it solves}
**Target Users**: {who uses it}
**Success Criteria**:
- {measurable metric 1}
- {measurable metric 2}
```

### Section 2: MVP Scope

This section is critical for task-list integration. Be explicit about boundaries.

```markdown
## 2. MVP Scope

### In Scope
- {feature 1}
- {feature 2}

### Out of Scope / Deferred
- {deferred feature 1} -- reason
- {deferred feature 2} -- reason

### Constraints
- {technical constraint}
- {business constraint}
```

### Section 3: User Flows

Use arrow notation for clarity. Each flow should be a numbered sequence.

```markdown
## 3. User Flows

### 3.1 {Flow Name}
1. User {action}
2. System {response}
3. User {action}
   - If {condition}: {branch}
   - If {error}: {error handling}
```

### Section 4: Information Architecture

Use tree structure for page/screen hierarchy.

```markdown
## 4. Information Architecture

{App Name}
  {Section 1}
    {Page 1}
    {Page 2}
  {Section 2}
    {Page 3}
```

### Section 5: Feature Specifications

Use a table format. Priority must use P0-P3 to match task-list.

```markdown
## 5. Feature Specifications

| Feature | Description | Priority | Acceptance Criteria |
|---------|-------------|----------|---------------------|
| {name}  | {what}      | P0       | {testable criteria} |

### Non-Functional Requirements
| Category    | Requirement                |
|-------------|----------------------------|
| Performance | {specific metric}          |
| Security    | {specific requirement}     |
```

### Section 6: Data Models

Use code blocks with field definitions. Include types and constraints.

```markdown
## 6. Data Models

### {Entity}
| Field       | Type         | Constraints       | Description |
|-------------|--------------|-------------------|-------------|
| id          | UUID         | PK                | {desc}      |
| name        | VARCHAR(100) | NOT NULL          | {desc}      |
| created_at  | TIMESTAMP    | DEFAULT now()     | {desc}      |

### Relationships
- {Entity A} 1:N {Entity B} (via {foreign_key})
```

### Section 7: API Design

Use HTTP method + path format. Include request/response schemas.

```markdown
## 7. API Design

### Authentication
{auth model description}

### Endpoints

#### {Group}

**{METHOD} {path}**
- Description: {what it does}
- Request:
  ```json
  { "field": "type" }
  ```
- Response:
  ```json
  { "field": "type" }
  ```
```

### Section 8: Technical Architecture

```markdown
## 8. Technical Architecture

### Tech Stack
| Layer      | Technology | Rationale          |
|------------|------------|--------------------|
| Frontend   | {tech}     | {why}              |
| Backend    | {tech}     | {why}              |
| Database   | {tech}     | {why}              |

### System Diagram
{text-based architecture diagram}

### Third-Party Dependencies
- {dependency}: {purpose}
```

### Section 9: Development Phases

Phase naming must use "Phase N: Name" format for task-list compatibility.

```markdown
## 9. Development Phases

### Phase 1: {Name}
**Scope**: {what's included}
**Deliverables**:
- {deliverable 1}
- {deliverable 2}

### Phase 2: {Name}
**Scope**: {what's included}
**Deliverables**:
- {deliverable 1}
```

### Section 10: Appendix

```markdown
## 10. Appendix

### Glossary
- {term}: {definition}

### Open Questions
- {question 1}

### References
- {reference}
```

---

## Adaptation Rules

Not every project needs every section. Apply these rules:

- **API-only / backend service**: Skip Section 4 (Information Architecture). Expand Section 7 (API Design).
- **Frontend-only**: Skip Section 7 (API Design) if no backend. Expand Section 4.
- **CLI tool**: Skip Sections 4 and 7. Add a "Commands" subsection in Section 5.
- **Library/SDK**: Skip Sections 3, 4. Add "Public API" subsection in Section 5.
- **Simple project** (< 3 features): Sections can be brief. Mark unused sections as "N/A".

## Language

Follow the user's input language. If the user writes in Chinese, write the PRD in Chinese (with English technical terms). If English, write in English.
