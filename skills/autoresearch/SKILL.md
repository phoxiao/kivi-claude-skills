---
name: autoresearch
description: Autonomous ML experiment loop inspired by Karpathy's autoresearch. Modifies training code, runs experiments with fixed time budgets, evaluates metrics, keeps improvements and discards failures via git. Use when the user wants to autonomously optimize ML training, run experiment loops, auto-tune hyperparameters, or set up autonomous research agents. Triggers include "autoresearch", "experiment loop", "autonomous training", "auto-optimize", "hyperparameter search".
argument-hint: setup <script-path> | run | status | analyze
---

# /autoresearch — Autonomous ML Experiment Loop

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). An AI agent autonomously modifies your training code, runs experiments on a fixed time budget, keeps improvements, discards failures, and iterates — all tracked via git commits and a results log.

## Subcommands

- `/autoresearch setup <script-path>` — Initialize a research session
- `/autoresearch run` — Start the autonomous experiment loop
- `/autoresearch status` — Show experiment progress dashboard
- `/autoresearch analyze` — Post-session analysis with recommendations

---

## `/autoresearch setup <script-path>`

Interactive setup phase. Read the code, agree on parameters, create a branch, initialize tracking.

### Steps

1. **Read the training script** at `<script-path>` and all related files in the same directory. Understand the framework (PyTorch, JAX, TensorFlow, etc.), model architecture, training loop, and evaluation logic.

2. **Ask the user to confirm or provide** these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `run_command` | How to execute training (e.g., `python train.py`, `uv run train.py`) | `python <script-path>` |
| `metric_name` | The evaluation metric to optimize (e.g., `val_loss`, `val_bpb`, `accuracy`) | *(must specify)* |
| `metric_direction` | `lower` (loss-like) or `higher` (accuracy-like) | `lower` |
| `metric_grep` | Grep pattern to extract metric from stdout (e.g., `^val_loss:`) | `^<metric_name>:` |
| `time_budget_minutes` | Minutes per experiment | `5` |
| `editable_files` | Files the agent may modify | `[<script-path>]` |
| `readonly_files` | Files to read for context but never modify | `[]` |
| `max_experiments` | Safety cap, 0 = unlimited | `50` |

3. **Propose a run tag** based on today's date (e.g., `mar23`). User may override.

4. **Create branch** `autoresearch/<tag>` from current HEAD:
```bash
git checkout -b autoresearch/<tag>
```

5. **Initialize `results.tsv`** with header row:
```
commit	<metric_name>	memory_gb	duration_s	status	description
```

6. **Save configuration** to `.autoresearch.json`:
```json
{
  "tag": "<tag>",
  "branch": "autoresearch/<tag>",
  "script_path": "<script-path>",
  "run_command": "<command>",
  "metric_name": "<name>",
  "metric_direction": "lower",
  "metric_grep": "^<name>:",
  "time_budget_minutes": 5,
  "timeout_minutes": 10,
  "editable_files": ["<script-path>"],
  "readonly_files": [],
  "max_experiments": 50,
  "created_at": "<ISO timestamp>"
}
```

7. **Add to `.gitignore`** (if not already present): `results.tsv`, `.autoresearch.json`, `run.log`

8. **Confirm setup** and show a summary. Await user's go-ahead before running.

---

## `/autoresearch run`

The core autonomous experiment loop. Once started, runs indefinitely until max_experiments or user interrupt.

### Pre-loop

1. Read `.autoresearch.json` for configuration
2. Verify you are on branch `autoresearch/<tag>`. If not, `git checkout autoresearch/<tag>`
3. Read all editable and read-only files for full context
4. Read `results.tsv` — if no data rows exist, the first experiment is the **baseline** (run the script as-is, record with status `baseline`)

### The Loop

**Repeat indefinitely:**

#### Step 1 — Plan
Based on previous results in `results.tsv`, current code state, and ML knowledge, decide what to try next. Use the [Experiment Strategy Guide](#experiment-strategy-guide) for ideas. Write a one-line description of the experiment before modifying code.

#### Step 2 — Modify
Edit the editable file(s) with the experimental change. **One idea per experiment** — never combine unrelated changes.

#### Step 3 — Commit
```bash
git add <editable-files>
git commit -m "exp: <short description>"
```

#### Step 4 — Run
Execute the training command with output redirected and a timeout:
```bash
timeout <timeout_minutes>m <run_command> > run.log 2>&1
```
Use the Bash tool with `timeout` set to `timeout_minutes * 60 * 1000` ms.

#### Step 5 — Evaluate
Extract the metric:
```bash
grep '<metric_grep>' run.log
```
If grep returns nothing, the run crashed. Go to Step 6a.

#### Step 6 — Decide

**6a. Crash:**
- Read the error: `tail -n 50 run.log`
- If simple fix (typo, import, shape mismatch): revert commit, apply fix, re-commit, re-run (max 2 retries)
- If fundamental (OOM, architecture incompatibility): log as `crash` and move on
- Record in `results.tsv`: metric=`0.000000`, memory_gb=`0.0`, duration_s=`0`, status=`crash`

**6b. Metric improved** (lower for `lower`, higher for `higher`):
- Status: `keep` — the branch advances, this commit stays
- Apply the **simplicity criterion**: if the improvement is tiny but the code got much more complex, consider treating as `discard`

**6c. Metric equal or worse:**
- Status: `discard` — revert the commit:
```bash
git reset --hard HEAD~1
```

#### Step 7 — Log
Append a row to `results.tsv`:
```
<commit-7chars>	<metric_value>	<memory_gb>	<duration_s>	<status>	<description>
```

Extract memory from run.log if available (grep for peak memory, VRAM, etc.). If not available, use `0.0`.

#### Step 8 — Continue
**Do NOT ask the user if you should continue. Do NOT pause.**
- If max_experiments reached → stop and output a final summary
- If 3 consecutive crashes → try a completely different approach category, then continue
- If out of ideas → re-read the code, re-read results, try combinations of near-misses, try more radical changes
- Otherwise → go to Step 1

### Output During Loop
After each experiment, print a one-line summary:
```
#<N>  <commit>  <metric_value>  <status>  <description>
```

---

## `/autoresearch status`

Show an ASCII dashboard of current progress.

### Steps

1. Read `.autoresearch.json` and `results.tsv`
2. Output:

```
================================================================
  AUTORESEARCH · <tag> · <script_path>
================================================================

  EXPERIMENTS  [################....] 16/50
  METRIC       <metric_name> (<direction>)

  BEST         <best_value>  (exp #<N>, commit <hash>)
  BASELINE     <baseline_value>
  IMPROVEMENT  <delta> (<percentage>%)

  RECENT EXPERIMENTS
  #16  a1b2c3d  0.993  keep     increase LR to 0.04
  #15  b2c3d4e  1.005  discard  switch to GeLU activation
  #14  c3d4e5f  0.000  crash    double model width (OOM)
  #13  d4e5f6g  0.995  keep     reduce depth to 6 layers

  STATUS BREAKDOWN
  keep:     8 (50%)
  discard:  5 (31%)
  crash:    3 (19%)
================================================================
```

---

## `/autoresearch analyze`

Post-session analysis. Run after stopping the loop.

### Steps

1. Read `.autoresearch.json` and `results.tsv`
2. Read the current state of all editable files (these reflect the accumulated "keep" changes)
3. Run `git log --oneline autoresearch/<tag>` to see kept commits
4. Generate and save `autoresearch-<tag>-analysis.md` with:

**Summary:**
- Total experiments, keep/discard/crash counts and rates
- Best metric value vs baseline, total improvement

**What Worked:**
- List all `keep` experiments with descriptions, grouped by category (hyperparams, architecture, optimizer, etc.)
- Highlight the single biggest improvement

**What Didn't Work:**
- List `discard` experiments, identify patterns (e.g., "all activation function changes were discarded")

**Crashes:**
- Root causes and lessons learned

**Metric Progression:**
- ASCII chart showing metric over experiment number, marking keeps vs discards

**Recommendations:**
- What to try next if continuing
- Which areas have unexplored potential
- Whether the returns are diminishing

5. Print the analysis to the user

---

## Experiment Strategy Guide

Ordered by risk level. Start low, escalate gradually.

### 1. Hyperparameters (Low Risk — try first)
- Learning rate: 2x, 0.5x, different schedules
- Batch size: larger (if memory allows), smaller
- Weight decay: 0, 0.01, 0.1, 0.2
- Warmup steps/ratio: 0%, 5%, 10%
- Gradient clipping: off, 1.0, 0.5
- Dropout: 0, 0.1, 0.2

### 2. Architecture (Medium Risk)
- Depth: +/- layers
- Width: model dimension changes
- Attention heads: count, head dimension
- Activation functions: ReLU, GELU, SiLU, ReLU², Swish
- Normalization: LayerNorm vs RMSNorm, pre-norm vs post-norm
- Position encoding: learned vs rotary (RoPE) vs ALiBi

### 3. Optimizer (Medium Risk)
- Optimizer type: Adam, AdamW, SGD+momentum, Lion, Muon
- Beta values: (0.9, 0.999) vs (0.9, 0.95) vs (0.8, 0.95)
- Epsilon: 1e-8 vs 1e-6
- LR schedule: cosine, linear, warmup-cosine, warmdown

### 4. Regularization (Low Risk)
- Label smoothing: 0.1
- Stochastic depth
- Gradient noise injection

### 5. Simplification (Always Valuable)
- Remove unused components
- Reduce unnecessary complexity
- Eliminate redundant computations
- If performance is maintained after removal → always `keep`

### Strategy Tips
- After a `keep`, try **variations on the same theme** (e.g., if LR 0.02 helped, try 0.03)
- After 3+ consecutive `discard` in one category, **switch categories**
- Periodically try **combining** multiple kept improvements that were found independently
- After many experiments, try **radical changes** (very different architecture, unusual techniques)
- **Read the loss curve** in run.log — underfitting vs overfitting suggests different directions

---

## Git Workflow

- Branch `autoresearch/<tag>` created from current HEAD
- Each experiment: commit BEFORE running (captures code state regardless of outcome)
- `keep` → commit stays, branch advances
- `discard` → `git reset --hard HEAD~1` reverts
- `crash` (with fix) → revert failing commit, apply fix, new commit, re-run
- `results.tsv`, `.autoresearch.json`, `run.log` are **untracked** (in .gitignore)
- Branch history is clean: only successful experiments in the git log
- After the session, the branch can be merged into main or kept for reference

---

## Rules

- NEVER modify files not listed in `editable_files`
- NEVER install new packages or add dependencies
- NEVER modify the evaluation metric computation
- NEVER commit `results.tsv`, `.autoresearch.json`, or `run.log` to git
- NEVER stop the loop to ask the user for permission to continue
- NEVER let training output flood the context — always redirect to `run.log`
- ALWAYS commit before running (captures code state)
- ALWAYS redirect output: `<command> > run.log 2>&1`
- ALWAYS read the error on crash: `tail -n 50 run.log`
- ALWAYS apply the simplicity criterion: complexity cost vs. improvement magnitude
- ONE idea per experiment — never combine unrelated changes
- If metric is equal (not improved), treat as `discard`
- Each experiment description must be unique and descriptive

## Anti-Patterns

- Making multiple unrelated changes in one experiment
- Increasing model size dramatically without checking memory first
- Repeating the same type of change that keeps crashing
- Over-optimizing one hyperparameter while ignoring architecture
- Adding complexity for marginal gains
- Modifying evaluation code to game the metric
- Running experiments without redirecting output (context overflow)
