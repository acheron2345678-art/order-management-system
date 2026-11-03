# Phase 12H — Local Order Management AI performance

This optimization does **not** cache report values, model interpretations,
restaurant assignments, account roles, or signed conversation tokens.
FastAPI still checks permissions and re-queries authorized MySQL aggregates
on every report or analysis request.

## What's changed

- Five narrow families of unambiguous analysis questions go directly to the
  existing authorized analysis service, saving **one Ollama intent-classifier
  request** for those cases. Unfamiliar/ambiguous wording still uses the
  structured-output Qwen classifier.
- The three Ollama chat paths (general Order Management guidance, structured
  intent classification, grounded analysis) send an explicit `keep_alive`
  parameter, to reduce model reloads during an active chat session.
- Optional logs report model loading, prompt evaluation, generation time,
  token counts and total wall time. Prompts, responses, names, order details and
  personal information are not logged by the added instrumentation.

## Windows PowerShell settings

Use in the **same PowerShell session before starting Uvicorn**:

```powershell
cd E:\order-management-system-main
.\.venv\Scripts\Activate.ps1
$env:OM_AI_KEEP_ALIVE = "10m"
$env:OM_AI_LOG_TIMINGS = "1"
python -m uvicorn app.main:app --reload
```

`OM_AI_KEEP_ALIVE` accepts `0` or a positive integer followed by `s`, `m`, or
`h`. The default is `10m`; invalid values also fall back to `10m`.
Keeping the model resident uses GPU/CPU memory while it is retained. If you
want to free VRAM for gaming, shut down the Ollama model with `ollama stop
<model-name>` when not using the assistant, or use a shorter keep-alive value.
Setting `0` unloads after each response, which saves idle memory but usually
makes the next question slower.

`OM_AI_LOG_TIMINGS` defaults to off. When enabled, look in the **Uvicorn
terminal**, not the browser console, for entries similar to:

```text
Ollama analysis wall=3.120s total=3.000s load=0.250s prompt=0.500s generate=2.000s prompt_tokens=1250 output_tokens=80
```

The line above is illustrative, **not** a measured benchmark. Ollama timing
fields are reported in nanoseconds and converted to seconds.

## How to compare before and after

1. With your City Kitchen merchant account, ask the same in-scope query
   (`Do I have enough stock to handle more orders?`) in a fresh conversation.
2. Compare the number of `Ollama intent` lines; the new fast path should
   create **zero** for that exact request. Expect an `Ollama analysis` line
   for successful model-generated interpretation (possibly two if validation
   forces a retry).
3. Ask an ambiguous operations question (`Should I focus on improving
   operations?`) and expect the existing `Ollama intent` call.
4. Re-run the exact report (`Show my restaurant performance for September
   2026`). It should use FastAPI's deterministic report path and not call
   Ollama.
5. Test another restaurant (`How is KFC doing these days?`) and confirm the
   existing permission error. Test `pokemon` and confirm domain refusal.
6. Check `ollama ps` in another PowerShell window to confirm whether your
   model is loaded on GPU. Record cold and warm wall time separately.

No speed-up percentage is claimed without a live comparison on your computer.
