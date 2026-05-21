<div align="center">

# Basis

**An autonomous research agent that finds real documents, reads them, and returns scored trade ideas.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-meraki.prateekjain.io-blue?style=flat-square&logo=vercel)](https://meraki.prateekjain.io)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Table of Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Environment](#environment)
- [Current limitations](#current-limitations)
- [Disclaimer](#disclaimer)
- [License](#license)

## What it does

Basis is a research pipeline, not a chatbot wrapper. You state an investment thesis — "AI infrastructure for the next decade" — and it:

1. **Searches** the open web for PDF research reports, SEC filings, and whitepapers
2. **Downloads** the best candidates in parallel, validates them (magic bytes, content-type, size)
3. **Parses** them into structured text with preserved table structure (LlamaParse + PyMuPDF fallback)
4. **Indexes** passages into a per-session vector store (Qdrant)
5. **Retrieves** relevant context and synthesizes a structured thesis via LLM
6. **Scores** every recommended stock on a 5-factor rubric using live market data (yfinance)
7. **Persists** the full thesis + trade journal so follow-up questions reuse the corpus

Follow-ups do not re-search. They load the existing document index, blend conversation history into the retrieval query, and adjust positions.

### Why this instead of...

| Tool | What it does | What Basis adds |
|---|---|---|
| **ChatGPT / Claude** | General reasoning on stale training data | Live document retrieval + source attribution + live fundamentals |
| **[GPT Researcher](https://github.com/assafelovic/gpt-researcher)** | Deep web research reports | Trade scoring with live market data + position tracking |
| **[AI Hedge Fund](https://github.com/virattt/ai-hedge-fund)** | Multi-agent persona-based analysis | Real document discovery (not just API data) + persistent corpus |
| **[OpenBB](https://github.com/OpenBB-finance/OpenBB)** | Financial data platform | Autonomous thesis-driven research + synthesis |

## How it works

```
User → Frontend (Next.js / Vercel) → Backend (FastAPI / Cloud Run)
                                           │
                     ┌─────────────────────┼─────────────────────┐
                     ▼                     ▼                     ▼
               Qdrant (vectors)       Supabase (sessions)      LLM (OpenAI)
```

**Pipeline**

| Step | Action | Details |
|------|--------|---------|
| Discover | Web search + URL scoring | 4 query strategies, 30 candidates scored on domain authority |
| Download | Parallel fetch + validation | Magic-byte validation, size checks, 20s timeout |
| Parse | PDF → structured text | LlamaParse primary, PyMuPDF fallback |
| Index | Chunk + embed → Qdrant | Per-session collections, OpenAI embeddings |
| Retrieve | Semantic search | Top-8 passages blended with conversation context |
| Synthesize | LLM → structured thesis | JSON output: theme, conviction, summary, stock list |
| Score | yfinance + 5-factor rubric | Fundamentals 30%, Thematic fit 25%, Risk 20%, Momentum 15%, Liquidity 10% |
| Track | Persist to Supabase | Full trade journal with rationale, entry, target, stop |

**5-Factor Scoring Rubric**

| Factor | Weight | Source |
|--------|--------|--------|
| Fundamentals | 30% | P/E, ROE, revenue growth, margins |
| Thematic fit | 25% | LLM judgment from document context |
| Risk | 20% | Debt/equity, market cap, 52W range |
| Momentum | 15% | Revenue growth trajectory |
| Liquidity | 10% | Market cap |

## Quickstart

### Prerequisites

- Python 3.13
- Node.js 20+
- Docker (for local Qdrant)

### Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add OPENAI_API_KEY to .env
```

### Frontend

```bash
cd frontend
npm install
```

### Run

```bash
docker compose up -d qdrant

# Terminal 1
cd backend && uvicorn src.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:3000.

## Usage

### Web UI

Visit the chat interface and type a thesis:

```
"I want to bet on AI infrastructure over the next decade"
```

Basis will search, download, parse, and return scored positions.

### API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "AI infrastructure buildout"}]}'
```

### Follow-ups

Follow-up questions reuse the indexed corpus:

```
"What if China bans AI chip exports?"
```

This adjusts existing positions without re-searching.

## Project Structure

```
backend/
  src/
    agent.py              # Orchestrator: discover → parse → index → retrieve → score
    main.py               # FastAPI: /chat, /sessions, /health
    tools/
      document_fetcher.py # Multi-strategy search + scoring
      document_parser.py  # LlamaParse + PyMuPDF fallback
      vector_store.py     # Qdrant session manager
      stock_scorer.py     # yfinance + rubric
      web_search.py       # Tavily / DuckDuckGo
frontend/
  app/(chat)/             # Next.js chat UI
  components/chat/        # Message threads, input, sidebar
  lib/ai/models.ts        # Model definitions
  lib/db/queries.ts       # Database stubs
```

## Deployment

**Backend → Google Cloud Run**

```bash
cd backend
gcloud builds submit --tag gcr.io/PROJECT/basis-backend
gcloud run deploy basis-backend --image gcr.io/PROJECT/basis-backend --allow-unauthenticated
```

**Frontend → Vercel**

```bash
cd frontend
vercel --prod
```

## Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM synthesis + embeddings |
| `QDRANT_URL` | Yes | Vector store (local or Qdrant Cloud) |
| `QDRANT_API_KEY` | For Cloud | Qdrant Cloud authentication |
| `SUPABASE_URL` | Yes | Session + trade persistence |
| `SUPABASE_KEY` | Yes | Supabase service role key |
| `TAVILY_API_KEY` | Optional | Premium web search (falls back to DDG) |
| `LLAMA_CLOUD_API_KEY` | Optional | PDF parsing (falls back to PyMuPDF) |

## Current Limitations

- **LLM quota**: OpenAI key required for synthesis and embeddings. No local embedding model yet.
- **Cloud Qdrant**: Cloud Run → Qdrant Cloud returns 403; using in-memory fallback on Cloud Run.
- **Follow-up noise**: Blending conversation history into retrieval query is heuristic, not learned.
- **yfinance throttling**: Heavy use triggers rate limits. Partial data returned.

## Disclaimer

This is an experimental research tool, not investment advice. The scores and recommendations are generated by an LLM reading publicly available documents and financial data. They do not constitute a recommendation to buy, sell, or hold any security. Always do your own research and consult a qualified financial advisor before making investment decisions.

## License

MIT
