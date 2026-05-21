# basis

Agent that searches the web for investment PDFs, reads them, and returns scored stock theses.

Type a theme like "AI infrastructure" — it finds reports, parses tables, indexes them, retrieves relevant passages, asks an LLM for stock picks, and scores them with real yfinance data.

> ⚠️ **Needs a real OpenAI API key** for the LLM + embedding step. Everything else (document search, download, parse, stock scoring) works without it.

## quickstart

```bash
git clone https://github.com/prateekjain98/basis.git
cd basis

# backend
cd backend
cp .env.example .env
# edit .env: add OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

Run:

```bash
# terminal 1: infra
docker compose up -d qdrant

# terminal 2: backend (port 8000)
cd backend && source .venv/bin/activate && uvicorn src.main:app --reload

# terminal 3: frontend (port 3000)
cd frontend && npm run dev
```

Open http://localhost:3000.

No OpenAI key? Use [OpenRouter](https://openrouter.ai) free models:
```
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.1-70b-instruct
```

## how it works

`backend/src/agent.py` (~200 lines). Two modes:

**First turn** — full pipeline:
```
search (4 DDG queries → 30 candidates → score URLs → download top 15)
→ parse (LlamaParse, table-aware)
→ index (chunk + embed → Qdrant)
→ retrieve (top-8 passages)
→ synthesize (LLM → JSON with stocks)
→ score (yfinance + 5-factor rubric)
→ persist (Supabase)
```

**Follow-up** — skip discovery, reuse index. Blends conversation history into retrieval query.

## what works without OpenAI

Document discovery and stock scoring are testable immediately:

```python
from backend.src.tools.document_fetcher import DocumentFetcher
from backend.src.tools.stock_scorer import StockScorer

# finds ~30 PDFs, scores them, returns best 5
docs = DocumentFetcher().find_and_download("renewable energy", top_n=5)
# → [{'title': '...', 'url': '...', 'score': 0.65, 'path': '...'}, ...]

# real yfinance data
scores = StockScorer().score("AAPL")
# → {'fundamentals_score': 85, 'risk_score': 75, 'metrics': FinancialMetrics(...)}
```

Run tests:
```bash
cd backend && pytest ../tests/test_agent.py -v
```

## stack

- **FastAPI** + Pydantic backend
- **Supabase** (Postgres + REST API) for sessions, stocks, docs, messages
- **Qdrant** for vectors
- **LlamaParse** for PDF parsing (optional)
- **yfinance** for financial data (free, no key)
- **Next.js** + Vercel AI SDK for frontend

## deploy

```bash
# backend → Fly.io
fly launch --dockerfile backend/Dockerfile

# frontend → Vercel
vercel --prod
```

Costs $0 at rest on free tiers.

## files

| file | what |
|------|------|
| `backend/src/agent.py` | orchestrator |
| `backend/src/tools/document_fetcher.py` | find 30 PDFs, return best 5 |
| `backend/src/tools/stock_scorer.py` | yfinance + rubric |
| `frontend/app/(chat)/api/chat/route.ts` | proxy to backend |
| `backend/schema.sql` | Supabase table definitions |

## license

MIT
