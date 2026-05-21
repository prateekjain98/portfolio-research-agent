# Architecture Decisions

## ADR-1: Task — Thematic Investment Research

**Decision:** Build a conversational agent that researches investment themes, discovers documents, and returns scored stock recommendations with session memory.

**Why this task:**
- Inherently multi-step: search → fetch → parse → index → retrieve → score
- Requires ≥2 tools: document discovery, financial data, vector search
- Session memory is meaningful: follow-ups reuse the document corpus
- Financial data provides a clear correctness signal for evals

**Trade-offs:**
- (+) Strong eval signal — verify claimed financials against real data
- (-) Requires live web search and PDF parsing — more failure modes than closed-domain tasks

---

## ADR-2: Backend — FastAPI + Pydantic

**Decision:** Use FastAPI with Pydantic models.

| Option | Rejected because |
|--------|-----------------|
| Flask | No native async; no auto-generated OpenAPI |
| Django | Too heavy; ORM conflicts with Supabase |
| LangChain | See ADR-6 |

**Rationale:** The pipeline is I/O bound (web search, PDF download, LLM calls). FastAPI's async/await is essential. Pydantic gives runtime validation and auto-generated `/docs`.

**Trade-offs:**
- (+) Clean API docs automatically
- (-) We write orchestration manually in `agent.py`

---

## ADR-3: Database — Supabase

**Decision:** Use Supabase (Postgres + REST API) instead of SQLAlchemy + Alembic.

**Rationale:**
- Auto-generated REST API — no ORM boilerplate
- Schema managed via Supabase CLI migrations
- Python client is sync-only; we wrap calls in `asyncio.to_thread()`

**Schema:**
```sql
thesis_sessions      -- id, user_query, theme, summary, conviction
documents            -- id, thesis_id, url, title, parsed_content
stock_recommendations -- id, thesis_id, ticker, name, entry_price, total_score
messages             -- id, session_id, role, content
```

**Trade-offs:**
- (+) Zero ORM code
- (-) Less type safety; compensated by Pydantic schemas in `models/schemas.py`

---

## ADR-4: Vector Store — Qdrant

**Decision:** Use Qdrant for embeddings. One collection per session.

| Option | Rejected because |
|--------|-----------------|
| pgvector | Shares RAM with OLTP; slows past ~1M vectors |
| Pinecone | Separate account; pricing complexity |
| Chroma | In-process only; harder to deploy |

**Rationale:**
- Single Docker container locally, managed cloud in production
- HNSW is default — no tuning needed for ~500 chunks/session
- Per-session collections make deletion trivial

**Trade-offs:**
- (+) Fast semantic search out of the box
- (-) Linear memory growth with sessions

---

## ADR-5: Document Parsing — LlamaParse + PyMuPDF

**Decision:** LlamaParse primary, PyMuPDF fallback.

**Rationale:**
- PyMuPDF scrambles multi-column financial reports (table rows interleaved with footnotes)
- LlamaParse preserves table structure and converts charts to markdown
- Without a LlamaParse key, the pipeline falls back to PyMuPDF or web snippets — no crash

---

## ADR-6: Orchestration — Plain Python, Not LangChain

**Decision:** Do not use LangChain or LangGraph. Implement the pipeline in plain Python.

**Rationale:**

1. **Linear pipeline.** Our flow is fixed: `search → fetch → parse → index → retrieve → score`. There is no decision-making at each step. LangChain's ReAct loop adds complexity without capability.

2. **Follow-ups are simple.** Session memory is 15 lines: load history, blend into retrieval query, call LLM. LangChain's `ConversationBufferMemory` wraps the same logic in 3 abstraction layers.

3. **Debugging.** When the LLM wraps JSON in markdown fences, the fix is one line after `chat.completions.create()`. In LangChain, we'd dig through `JSONOutputParser` internals.

**When LangGraph would be worth it:** If we added a second agent (e.g., a risk analyst that argues with the main researcher), then DAG state management becomes justified.

---

## ADR-7: Financial Data — yfinance

**Decision:** Use yfinance for live stock fundamentals.

| Option | Rejected because |
|--------|-----------------|
| Bloomberg | $24k/year license |
| Alpha Vantage | 5 req/min free tier |
| Polygon.io | $199/mo minimum |

**Rationale:** Free, no API key, returns P/E, margins, growth, debt. The scorer catches all exceptions and returns partial data; missing fields default to 50/100.

**Trade-offs:**
- (+) Zero cost
- (-) Rate-limits after ~20 tickers; no SLA

---

## ADR-8: Frontend — Next.js + Vercel AI SDK

**Decision:** Use Next.js 16 with Vercel AI SDK for the chat UI.

**What we kept from the starter template:**
- Chat shell and message threading
- `useChat` hook for SSE streaming
- API route proxy pattern

**What we stripped:**
- Auth system → dummy auth
- AI Gateway references
- Artifact rendering
- Model selector
- Credit card alert

**Rationale:** The Vercel AI SDK handles streaming, error states, and abort signals correctly. Re-implementing SSE in raw React is error-prone.

---

## ADR-9: LLM Provider — Multi-provider

**Decision:** Support OpenAI, Anthropic, and Vertex AI. All use the same `_llm_chat()` abstraction.

**Rationale:**
- OpenAI default: `gpt-4o-mini` supports JSON mode, cheap
- Swapping providers is one env var change — zero code changes
- For local development, Ollama (`mistral:latest`) is wired in via `OPENAI_BASE_URL`

---

## ADR-10: Session Memory

**Decision:** Dual-layer session memory.

1. **Document corpus persistence:** Documents from the first turn are saved to Supabase and indexed in Qdrant. Follow-ups check for existing documents; if found, skip search/fetch/parse/index.

2. **Message history blending:** Follow-ups concatenate the last 4 messages into the retrieval query.

```python
if is_followup and len(history) >= 2:
    recent = history[-4:]
    retrieval_query = " | ".join(
        f"{m['role']}: {m['content'][:100]}" for m in recent
    )
    retrieval_query += f" | now: {query}"
```

**Trade-offs:**
- (+) Fast follow-ups: ~2s vs ~30s for full discovery
- (+) Consistent grounding across the session
- (-) Heuristic blending is fragile on topic switches
