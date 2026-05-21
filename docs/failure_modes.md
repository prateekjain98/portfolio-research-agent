# Failure Modes

Categorized by severity: P0 (blocking), P1 (degraded), P2 (cosmetic).

---

## P0 — Blocking

### 1. No working LLM provider

**What breaks:** Agent discovers and parses documents, then dies at LLM synthesis. Returns empty thesis.

**Root cause:** OpenAI key exhausted ($10 credit → 429); Anthropic key expired (404); Vertex AI has no model access (404).

**Mitigation:** Agent catches exception, returns fallback thesis with no stocks, logs error.

**Fix:** Wire Ollama (`mistral:latest` on `localhost:11434`) into `_llm_chat()`. Effort: 2–3 hours.

### 2. Frontend crashes on empty model list

**What breaks:** White screen. Console: `Cannot read properties of undefined (reading 'id')`.

**Root cause:** `/api/models` returns `{models: []}`. `useActiveChat` does `activeModels[0]` without guard.

**Fix:** Return hardcoded model from `/api/models` or add guard in `use-active-chat.tsx`. Effort: 15 minutes.

### 3. Cloud Run → Qdrant Cloud 403

**What breaks:** Vector indexing/search fail on deployed backend. Falls back to in-memory keyword search.

**Root cause:** Cloud Run missing `QDRANT_API_KEY` env var.

**Fix:** Set `QDRANT_API_KEY` in Cloud Run. Effort: 5 minutes.

---

## P1 — Degraded

### 4. LLM returns markdown-wrapped JSON

**What breaks:** ~30% of GPT-4o-mini responses wrap JSON in fences. `json.loads()` throws.

**Root cause:** Model ignores `response_format={"type": "json_object"}` intermittently.

**Mitigation:** `.removeprefix("```json")` before parsing.

**Fix:** Retry on parse failure with strict JSON mode. Effort: 30 minutes.

### 5. yfinance rate-limits

**What breaks:** After ~20 tickers, scores show `None`. Rubric returns neutral 50s.

**Root cause:** Yahoo Finance blocks IPs after rapid requests.

**Mitigation:** Catch exceptions, return partial data. Missing fields default to 50/100.

**Fix:** Batch requests with 1s delays; add fallback data source. Effort: 2–3 hours.

### 6. Follow-ups retrieve wrong context

**What breaks:** After NVDA thesis, "what about risks?" retrieves "AI risk management frameworks" instead of "risks of NVDA stock."

**Root cause:** Retrieval query blends last 4 messages heuristically. No understanding that "risks" refers to previously recommended stocks.

**Fix:** Inject previous stock tickers into follow-up retrieval query. Effort: 2–4 hours.

### 7. DDG search returns garbage

**What breaks:** ~30% of downloaded "PDFs" are HTML landing pages or SEO spam.

**Root cause:** DuckDuckGo results are noisy without Tavily.

**Mitigation:** URL scoring filters junk; magic-byte validation rejects non-PDFs.

**Fix:** Add Tavily API key; validate Content-Type before download. Effort: 1 hour.

---

## P2 — Cosmetic

### 8. Qdrant collections grow unbounded

**What breaks:** Memory grows linearly with sessions.

**Root cause:** Per-session collection design. No automatic cleanup.

**Mitigation:** `DELETE /sessions/{id}` drops collection explicitly.

**Fix:** Nightly cron to delete collections for sessions older than 30 days. Effort: 1–2 hours.

### 9. Frontend template cruft

**What breaks:** Build warnings from unused imports; larger bundle.

**Root cause:** Vercel AI Chatbot template stripped but not fully cleaned.

**Fix:** Audit and remove unused components. Effort: 1 hour.

### 10. Non-deterministic evals

**What breaks:** Same query produces different documents across days.

**Root cause:** Web search results change daily.

**Fix:** Add `--use-cached-docs` flag to eval runner. Effort: 2–3 hours.
