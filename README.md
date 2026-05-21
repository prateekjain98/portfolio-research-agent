# basis

<p align="center">
  <b>Autonomous investment research agent.</b><br>
  Type a theme. It finds PDF reports, reads them, returns scored stock theses.
</p>

---

## what it does

Analysts spend hours reading 100-page investment reports. Basis does it in 60 seconds.

```
User: "invest in AI infrastructure"

Agent:
  → searched web, found 30 PDF candidates
  → scored URLs, downloaded top 15
  → parsed 2 real reports (Meketa, Brookfield)
  → indexed 89 chunks in Qdrant
  → retrieved top-8 relevant passages
  → asked LLM to synthesize thesis
  → scored 3 stocks with real yfinance data

Result: NVDA (87/100), VST (74/100), DLR (71/100)
        with conviction, entry prices, rationale
```

Follow-up questions reuse the same document corpus — no re-searching. Ask "what about the risks?" and it adjusts the thesis using already-indexed passages.

## demo

**Document discovery** — finds real PDFs from web search:

```bash
$ python -c "from backend.src.tools.document_fetcher import DocumentFetcher; \
  print(DocumentFetcher().find_and_download('AI infrastructure', top_n=3))"

[DocumentFetcher] 3 good docs out of 29 candidates
  → AI Infrastructure Investment WHITEPAPER - meketa.com | score=0.65
  → [PDF] building the backbone of AI. - Brookfield | score=0.49
  → [PDF] The-State-of-AI-Infrastructure-at-Scale | score=0.42
```

**Stock scoring** — real yfinance data:

```bash
$ python -c "from backend.src.tools.stock_scorer import StockScorer; \
  import json; s=StockScorer().score('NVDA'); \
  print(json.dumps({k:v for k,v in s.items() if k!='metrics'}, indent=2))"

{
  "fundamentals_score": 85,
  "risk_score": 75,
  "momentum_score": 75,
  "liquidity_score": 80
}
```

**API** — stream a thesis:

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"invest in AI infrastructure"}]}'
```

## quickstart

```bash
git clone https://github.com/prateekjain98/basis.git
cd basis

# backend
cd backend
cp .env.example .env
# edit .env — add OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

Run:

```bash
# infra
docker compose up -d qdrant

# backend (port 8000)
cd backend && source .venv/bin/activate && uvicorn src.main:app --reload

# frontend (port 3000)
cd frontend && npm run dev
```

Open http://localhost:3000.

> **Note:** Python 3.14 won't work. LlamaIndex C extensions fail. Use 3.13.

No OpenAI key? Use [OpenRouter](https://openrouter.ai) free models — zero code changes:
```
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.1-70b-instruct
```

## how it works

`backend/src/agent.py` — ~200 lines, plain Python. No LangChain.

| step | what | tool |
|------|------|------|
| search | 4 DDG queries, score 30 candidates | `document_fetcher.py` |
| download | top 15 in parallel, 20s timeout | `document_fetcher.py` |
| parse | LlamaParse → markdown (tables preserved) | `document_parser.py` |
| index | chunk + embed → Qdrant | `vector_store.py` |
| retrieve | top-8 passages for query | `vector_store.py` |
| synthesize | LLM reads passages → JSON thesis | OpenAI |
| score | yfinance + 5-factor rubric | `stock_scorer.py` |
| persist | Supabase | `supabase_client.py` |

Follow-ups skip search/parse/index. Blends conversation history into retrieval query.

## tests

```bash
cd backend
pytest ../tests/test_agent.py -v
```

Covers web search, document fetching, stock scoring. Vector store test skipped without real OpenAI key (embeddings).

## deploy

```bash
# backend + Qdrant → Fly.io
fly launch --dockerfile backend/Dockerfile

# frontend → Vercel
vercel --prod
```

$0/month at rest on free tiers.

## project layout

```
backend/src/
  agent.py              # pipeline
  main.py               # FastAPI: /chat, /sessions, /health
  tools/
    document_fetcher.py # find 30 PDFs, return best 5
    document_parser.py  # LlamaParse wrapper
    vector_store.py     # Qdrant session manager
    stock_scorer.py     # yfinance + rubric
    web_search.py       # Tavily / DDG
frontend/app/(chat)/api/chat/route.ts   # proxy to backend
docs/
  architecture.md       # stack decisions
  failure_modes.md      # known issues
```

## license

MIT
