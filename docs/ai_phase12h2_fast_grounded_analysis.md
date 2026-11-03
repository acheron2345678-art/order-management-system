# Phase 12H.2 — Faster grounded interpretations

This update addresses a real two-attempt log: 10.377 seconds followed by
9.543 seconds (both generated replies rejected). The **observed total 19.92
seconds is not a baseline for all requests**; it is one failed example.

## What changes

- The model's *first* analysis prompt now receives small **qualitative flags**
  derived from the already-authorized aggregate report. It never receives the
  report's restaurant name, recorded amounts, counts or month. This removes the
  immediate temptation to copy numerical data that our validator then rejects.
- FastAPI continues to fetch authorized MySQL aggregates on **every** request
  and appends the complete verified figures. No numerical facts come from Qwen.
- Target a single short paragraph; `num_predict` is capped at 128 output tokens
  for an initial assessment and 100 for brief follow-ups (both attempts).
- A failing answer still gets at most one targeted corrective retry. The model
  output cannot bypass the existing numeric, recency, historical status, stock,
  causal, domain and code-generation validation rules. If neither attempt
  passes, the safe deterministic guidance remains.
- No changes to user roles, restaurant assignment, MySQL schema, model, Ollama
  keep-alive, or GPU/context configuration.

## Install and verify (PowerShell)

```powershell
# Run inside E:\order-management-system-main after applying the patch.
python -m pytest tests/ -q
$env:OM_AI_KEEP_ALIVE = "10m"
$env:OM_AI_LOG_TIMINGS = "1"
python -m uvicorn app.main:app --reload
```

Use a merchant account with its assigned restaurant, and ask these on a fresh
conversation, **twice each**:

- Do I have enough stock to handle more orders?
- Which orders should I investigate first?
- Compare my sales and inventory situation.

Keep the Uvicorn log lines beginning with `Ollama analysis wall=` and any
`Grounded analysis response rejected` warnings. Compare:

1. Number of model attempts per request (one is the goal for valid responses).
2. `eval_count` and `eval_duration` (generated tokens and generation time).
3. Total end-to-end time; the timing logs exclude database and browser work.
4. Whether the answer is grounded and useful. **Do not remove safeguards just
   to make the latency lower.**

A response with ~80 output tokens at the measured ~17.4 tokens/second could
spend ~4.6s generating; this is an estimate, not a benchmark. Cold starts,
first-run compilation and output quality will affect real results.
