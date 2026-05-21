# finquill

> Conversational research agent that ingests institutional reports and synthesizes structured investment theses.

finquill is a multi-step conversational agent designed for a specific workflow: read whitepapers, market reports, and earnings data — then build a conviction-driven investment thesis with sourced rationale, key risks, and position sizing. It maintains session memory so you can iterate on a thesis across multiple turns without losing context.

Built as a **reliability-first** system: explicit state machine, structured outputs on every LLM call, and graceful degradation when data sources fail.

---

## What It Does

```
User: "Thesis on AI infrastructure buildout — GPUs, power, datacenters"

  Step 1: PLAN        → "Need capex data, need recent reports, need earnings context"
  Step 2: TOOL_CALL   → Financial data (NVDA, VST) + Web search (Leopold, McKinsey, 13Fs)
  Step 3: OBSERVE     → Collect metrics, report snippets, filing signals
  Step 4: SYNTHESIZE  → Structured thesis with conviction, rationale, risks, sizing

Output:
  ┌─────────────────────────────────────────────┐
  │  THEME: AI Infrastructure Buildout          │
  │  CONVICTION: HIGH                           │
  │                                             │
  │  RATIONALE                                  │
  │  1. Hyperscaler capex +36% YoY, 75% to AI │
  │  2. Power bottleneck = pricing power        │
  │  3. 13F confirmation: Coatue, Tiger long    │
  │                                             │
  │  RISKS                                      │
  │  1. DeepSeek-style efficiency gains         │
  │  2. $1.5T debt wall                         │
  │                                             │
  │  POSITION (5Cr corpus, 10% alloc):          │
  │  NVDA 30% | VST 25% | AVGO 15% | Cash 30%  │
  │                                             │
  │  SOURCES: yfinance, tavily, 13F filings     │
  └─────────────────────────────────────────────┘

User (follow-up): "What if DeepSeek kills GPU demand?"
  → Agent recalls active thesis, pulls DeepSeek analysis,
    checks Jevons Paradox applicability, adjusts conviction
```

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│ Orchestrator │────▶│ Tool Router  │────▶│ Financial Data   │
│  (Session    │◀────│              │◀────│ (yfinance)       │
│   Memory)    │     │              │     ├──────────────────┤
└──────────────┘     │              │────▶│ Web Search       │
     │               │              │◀────│ (Tavily / DDG)   │
     │               │              │     ├──────────────────┤
     │               │              │────▶│ Report Ingestor  │
     │               │              │◀────│ (PDF / 13F / memo)│
     │               └──────────────┘     └──────────────────┘
     │                      │
     ▼                      ▼
┌──────────────────────────────────────────────┐
│ Thesis Synthesizer (LLM, structured output)  │
│  → Executive Summary                         │
│  → Investment Rationale (sourced)            │
│  → Key Risks                                 │
│  → Conviction Level (High / Med / Low)       │
│  → Position Sizing                           │
└──────────────────────────────────────────────┘
```

| Component | Purpose | Tech |
|-----------|---------|------|
| **Orchestrator** | Explicit `plan → tool → observe → synthesize` loop; session state management | Python + Pydantic |
| **Financial Data Tool** | Stock prices, fundamentals, peer metrics | yfinance |
| **Web Search Tool** | Recent reports, news, filings, institutional positions | Tavily API + DuckDuckGo fallback |
| **Report Ingestor** | PDF whitepapers, VC memos, 13F filings, earnings transcripts | PyMuPDF + unstructured |
| **Thesis Synthesizer** | Structured investment thesis from raw data | OpenAI-compatible LLM with Pydantic response format |
| **Session Memory** | Multi-turn context: thesis evolution, conviction changes, source inventory | In-memory Pydantic state machine |

**Design choices:**
- **Raw Python, no frameworks** — Full transparency. An evaluator reads the orchestrator in 10 minutes.
- **Structured outputs everywhere** — Every LLM call returns a typed Pydantic model. No free-text parsing.
- **Graceful degradation** — If yfinance fails, thesis still builds from web data. If search fails, financials still ground the output.

## Quickstart

```bash
# 1. Clone
git clone https://github.com/prateekjain98/finquill.git
cd finquill

# 2. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Add OPENAI_API_KEY and TAVILY_API_KEY

# 4. Run
python src/agent.py "Thesis on AI infrastructure" --ticker NVDA

# 5. Follow-up (uses session memory)
python src/agent.py "What about the power bottleneck?" --session <id>
```

## Project Structure

```
finquill/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── agent.py                 # Orchestrator + CLI
│   ├── models/
│   │   └── schemas.py           # Pydantic: Thesis, SessionState, FinancialMetrics
│   ├── memory/
│   │   └── session.py           # Multi-turn session persistence
│   └── tools/
│       ├── financial_data.py    # yfinance integration
│       ├── web_search.py        # Tavily + DuckDuckGo
│       ├── report_ingestor.py   # PDF / 13F / transcript parsing
│       └── thesis_builder.py    # LLM structured synthesis
├── eval/
│   ├── test_cases.json          # 20+ test prompts
│   ├── run_eval.py              # Eval runner
│   └── metrics.py               # Task completion, hallucination, coherence
├── docs/
│   └── architecture.md          # ADR: framework, tool, and design decisions
└── tests/
    └── test_agent.py            # Tool reliability + graceful failure tests
```

## Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working agent with ≥2 tools + session memory | ✅ | `src/agent.py` |
| Architecture decision doc | ✅ | `docs/architecture.md` |
| Eval suite (task completion, hallucination, graceful failure) | ✅ | `eval/` |
| Failure write-up | ✅ | `docs/failure_modes.md` |

## Run the Eval Suite

```bash
python -m pytest tests/          # Unit tests
python eval/run_eval.py          # Task completion + hallucination eval
```

## License

MIT
