# Basis

<p align="center">
  <strong>Autonomous investment research. From thesis to trade.</strong>
</p>

<p align="center">
  <a href="https://meraki.prateekjain.io">Live Demo</a> ·
  <a href="#quickstart">Quickstart</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="https://github.com/prateekjain98/basis/issues">Issues</a>
</p>

---

## What is Basis?

Basis is an autonomous research agent for thematic investing. You state a thesis — "AI infrastructure for the next decade" — and it:

1. **Discovers** situational awareness documents (industry reports, whitepapers, SEC filings)
2. **Reads** and indexes them into a searchable corpus
3. **Reasons** like a hedge fund analyst: macro context, sector dynamics, competitive positioning
4. **Decides** exact trades with position sizing, entry prices, stop losses
5. **Tracks** the thesis over time as new information emerges

Follow-up questions adjust positions without re-researching the entire corpus.

## Demo

```
User: "I want to bet on AI infrastructure over the next decade"

Basis:
  → Found 5 relevant reports (Morgan Stanley, Brookfield, Dell)
  → Parsed 179K words into 571 indexed passages
  → Built macro context: data center capex 25% CAGR, power constraints
  → Selected 3 positions with conviction levels

  NVDA  — 3% allocation @ $224  → target $350  (High conviction)
  AVGO  — 2% allocation @ $421  → target $600  (Medium conviction)
  VST   — 1% allocation @ $82   → target $120  (Hedge: power utility)

User: "What if China bans AI chip exports?"

Basis:
  → Retrieved existing corpus on supply chain risk
  → Adjusted: reduced NVDA to 1.5%, added AMD (less China exposure)
  → New stop: NVDA $180, AVGO $350
```

## Quickstart

**Prerequisites**

- Python 3.13
- Node.js 20+
- Docker (for local Qdrant)

**Backend**

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

**Frontend**

```bash
cd frontend
npm install
```

**Run**

```bash
docker compose up -d qdrant

# Terminal 1
cd backend && uvicorn src.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:3000.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  Frontend   │────▶│   Backend   │
│  (Next.js)  │◀────│  (Vercel)   │◀────│ (Cloud Run) │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┼────────────────────────┐
                       │                        │                        │
                       ▼                        ▼                        ▼
                ┌─────────────┐        ┌─────────────┐         ┌─────────────┐
                │   Qdrant    │        │  Supabase   │         │    LLM      │
                │ (Vector DB) │        │  (Session   │         │ (OpenAI /   │
                │             │        │   + Trade   │         │  Anthropic) │
                └─────────────┘        │   Journal)  │         └─────────────┘
                                       └─────────────┘
```

**Agent Pipeline**

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
| `OPENAI_API_KEY` | Yes | LLM synthesis |
| `QDRANT_URL` | Yes | Vector store (local or Qdrant Cloud) |
| `QDRANT_API_KEY` | For Cloud | Qdrant Cloud authentication |
| `SUPABASE_URL` | Yes | Session + trade persistence |
| `SUPABASE_KEY` | Yes | Supabase service role key |
| `TAVILY_API_KEY` | Optional | Premium web search (falls back to DDG) |

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

## License

MIT
