# Portfolio Research Agent

A conversational agent for institutional-grade investment research. Given a company or theme, the agent conducts multi-step research — aggregating financial data and web sources — then synthesizes a structured investment thesis with conviction levels, key risks, and a price target rationale.

> **Built for:** PS 3 — Minimal Agent, Maximum Reliability  
> **Principle:** Rock-solid multi-step reasoning over feature sprawl.

---

## What It Does

1. **Takes a research prompt** — e.g., *"Build a thesis for Tata Motors"* or *"What's the bull case for AI datacenter plays in India?"*
2. **Gathers data** — Uses financial data APIs (stock fundamentals, prices) and web search to collect relevant information.
3. **Synthesizes a thesis** — Produces a structured output: Executive Summary, Investment Rationale (3-5 points), Key Risks, Conviction Level (High/Medium/Low), and a Target Price Range with justification.
4. **Iterates with you** — You can challenge assumptions, ask for deeper dives, or pivot the thesis. The agent maintains session context.

## Architecture

```
User Input (research prompt)
    │
    ▼
┌─────────────┐     ┌──────────────┐
│ Orchestrator│────▶│  Tool Router │
│  (Memory)   │◀────│              │
└─────────────┘     └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌──────────┐
        │ Financial│  │  Web     │  │  Thesis  │
        │  Data    │  │  Search  │  │ Synthesizer│
        │  Tool    │  │  Tool    │  │  (LLM)    │
        └─────────┘  └──────────┘  └──────────┘
```

| Component | Purpose | Tech |
|-----------|---------|------|
| **Orchestrator** | Manages conversation flow, tracks session state, decides next action | Python + Pydantic |
| **Financial Data Tool** | Fetches stock prices, fundamentals, financial statements | `yfinance` / custom data source |
| **Web Search Tool** | Gathers recent news, analyst opinions, industry data | Web search API |
| **Thesis Synthesizer** | Structures raw data into an investment thesis | LLM with structured output |
| **Session Memory** | Persists conversation context across turns | In-memory + Pydantic models |

## Tools (≥ 2 Required)

1. **Financial Data Tool** — Gets real-time and historical stock data, balance sheet, income statement, cash flow.
2. **Web Search Tool** — Finds recent news, earnings transcripts, analyst reports, and industry context.
3. **Thesis Synthesizer** *(derived tool)* — Structured output generator that formats findings into an institutional-quality thesis.

## Session Memory

The agent tracks across the conversation:
- **Research target** (company, sector, theme)
- **Data collected** (financial metrics, news snippets, sources)
- **Thesis versions** (evolution of the investment case)
- **User corrections / pivots** (so follow-ups are grounded)

This lets you say *"Add a section on competitive moats"* or *"What if commodity prices drop 20%?"* and the agent knows exactly what you're referring to.

## Eval Suite

Metrics tracked:

| Metric | How |
|--------|-----|
| **Task completion rate** | % of prompts that produce a complete thesis |
| **Tool hallucination** | Does the agent invent data, or always ground in tool output? |
| **Graceful failure** | When a tool fails (e.g., ticker not found), does it recover or crash? |
| **Session coherence** | Does follow-up context carry correctly across turns? |

## Project Structure

```
├── README.md                 # This file
├── requirements.txt          # Python deps
├── .env.example              # API keys template
├── src/
│   ├── __init__.py
│   ├── agent.py              # Main orchestrator + conversation loop
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── financial_data.py # Stock/fundamentals tool
│   │   ├── web_search.py     # News/context search tool
│   │   └── thesis_builder.py # LLM synthesis tool
│   ├── memory/
│   │   ├── __init__.py
│   │   └── session.py        # Session state management
│   └── models/
│       ├── __init__.py
│       └── schemas.py        # Pydantic models for inputs/outputs
├── eval/
│   ├── __init__.py
│   ├── test_cases.json       # 20+ test prompts
│   ├── run_eval.py           # Eval runner
│   └── metrics.py            # Scoring logic
├── docs/
│   └── architecture.md       # ADR: framework choice, tool decisions
└── tests/
    └── test_agent.py         # Unit tests for tool + memory reliability
```

## Getting Started

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/portfolio-research-agent.git
cd portfolio-research-agent

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API keys (LLM provider, web search, etc.)

# Run
python src/agent.py
```

## Why This Framework

See [`docs/architecture.md`](docs/architecture.md) for the full ADR. Key decisions:

- **No heavy frameworks** — Raw Python with Pydantic for control and transparency. The evaluator should understand the agent in 10 minutes.
- **Explicit state machine** — Every turn is `plan → tool call → observe → synthesize`. No black-box "agent loops."
- **Structured outputs everywhere** — Every LLM call returns typed Pydantic objects, not free text. This prevents hallucination and makes eval deterministic.

## Known Limitations

| Limitation | Why | Fix Priority |
|------------|-----|-------------|
| Single-session memory only | No persistence layer yet | Low for PS3 scope |
| Web search quality depends on search API | Garbage in, garbage out | Medium — add source reliability scoring |
| No real-time price streaming | Polling only | Out of scope |
| Financial data limited to yfinance coverage | Exchange coverage gaps | Medium — add fallback data source |

## License

MIT
