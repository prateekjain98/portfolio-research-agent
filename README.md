# finquill

> *Every trade starts with a thesis. Every thesis starts with a signal others missed.*

**finquill** is a conversational research agent that reads institutional-grade whitepapers, VC memos, hidden market reports, and geopolitical intelligence — then synthesizes structured investment theses for retail investors who want to invest like the top 1%.

You have capital. You read Leopold's *Situational Awareness*. You know the top hedge funds have teams of researchers digesting signals you never see. **finquill** is that research team, in code.

---

## The Problem

Top investors operate on signals you don't have access to:

- **Leopold Aschenbrenner** reads classified-equivalent AI intelligence, writes 165-page monographs, then launches a $1.5B fund off the thesis.
- **Tiger Global** deploys analysts in Bangalore reading every startup pitch deck before you hear the name.
- **Andreessen Horowitz** circulates 50-page internal memos on sector rotations that never leave the building.
- **Renaissance Technologies** builds proprietary datasets from satellite imagery, credit card receipts, and shipping manifests.

Meanwhile, you're scrolling Twitter and buying based on vibes. You have 5Cr. You want to take 10% exposure on a conviction. But where does the conviction come from?

**finquill** closes that gap.

## What It Does

### The Flow

```
INGEST                SYNTHESIZE            ALLOCATE              EXECUTE
  |                      |                      |                    |
  v                      v                      v                    v
+----------+        +-------------+        +-------------+       +----------+
| Read     |------->| Build       |------->| Set         |------>| Track    |
|whitepaper|        | investment  |        | conviction  |       | thesis   |
| VC memos |        | thesis      |        | & position  |       | vs P&L   |
| 13F      |        | (structured)|        | size        |       |          |
| filings  |        |             |        |             |       |          |
| Earnings |        |             |        |             |       |          |
|transcript|        |             |        |             |       |          |
+----------+        +-------------+        +-------------+       +----------+
    ^                                              |
    +----------- Session Memory <------------------+
     (thesis evolution, conviction changes, follow-ups)
```

### Example Session

**You:** *"I read Leopold's Situational Awareness. The AI infrastructure buildout thesis -- GPUs, power, datacenter real estate. What's the play?"*

**finquill** (reads Leopold's paper, pulls recent 13F filings, checks hyperscaler capex commitments, reads earnings transcripts from NVDA, VST, INSM, then builds a thesis):

```
THEME: AI Infrastructure Buildout -- The Trillion-Dollar Cluster

EXECUTIVE SUMMARY
  The thesis Leopold laid out in June 2024 is accelerating faster than
  projected. Hyperscaler capex is consuming 2.2% of US GDP. $5.2T in
  datacenter buildout through 2030 per McKinsey. The bottleneck has
  shifted from GPUs to power -- every transformer, every HVDC cable,
  every acre near a nuclear plant is a strategic asset.

CONVICTION: HIGH

INVESTMENT RATIONALE
  1. Capex acceleration: Big 5 hyperscalers projected to spend $602B in
     2026 (+36% YoY), 75% directed to AI infra. Backlog extends to 2030.
  2. Power constraint = pricing power: Nuclear restarts (VST, INSM),
     gas turbine demand (GE Vernova), HVDC transmission (PRYS, NKT)
     all have multi-year order books.
  3. 13F confirmation: Situational Awareness LP holds VST, Broadcom,
     CoreWeave. Coatue increased NVDA. Tiger added SMCI.
  4. Geographic alpha: India grid-connected datacenter capacity is
     400MW today, targeting 5GW by 2028. Only 3-4 players have land
     + power locked.

KEY RISKS
  1. Efficiency revolution: DeepSeek proved GPT-4 parity at 1/18th cost.
     If inference-time compute scaling replaces training clusters,
     GPU demand thesis weakens.
  2. Debt wall: $1.5T in projected AI debt. 94% of hyperscaler OCF
     consumed by capex. Bank of America: "hitting a money wall."
  3. Geopolitical: Export controls on H20 chips to China could
     bifurcate supply chains, hurting revenue for US semiconductor
     companies.

POSITION SIZING (for 5Cr corpus, 10% allocation = 50L)
  Core positions (70% of allocation = 35L):
    - NVDA 30% (10.5L) -- monopoly on training + inference
    - VST 25% (8.75L) -- nuclear restart leader, power bottleneck play
    - Broadcom 15% (5.25L) -- custom silicon + VMware datacenter infra

  Satellite (30% of allocation = 15L):
    - INSM 15% (5.25L) -- India power/datacenter convergence
    - NKT/PRYS 10% (5L) -- HVDC cable duopoly
    - Cash 5% (2.5L) -- dry powder for pullbacks

TARGET HOLD: 18-24 months, re-evaluate at each hyperscaler capex guide

SOURCES
  - Situational Awareness (Aschenbrenner, June 2024)
  - McKinsey Datacenter Outlook (April 2025)
  - Recent 13F filings (Situational Awareness LP, Coatue, Tiger)
  - Q1 2026 earnings transcripts (NVDA, VST, AVGO)
```

**You:** *"What if DeepSeek-style efficiency gains kill the GPU demand story?"*

**finquill** (knows you were talking about the AI infra thesis, pulls recent DeepSeek analysis, checks if Jevons Paradox applies, updates conviction):

```
FOLLOW-UP: DeepSeek Efficiency Risk on AI Infra Thesis

Jevons Paradox applies here -- making AI cheaper INCREASES total spend
because demand expands faster than costs decline. Evidence:
  - Hyperscaler capex GUIDES RAISED post-DeepSeek, not lowered
  - Shift is from training to inference-time scaling (MORE compute,
    not less, just at inference)
  - o1/R1 models cost 10-100x more inference compute than base models

CONVICTION: HIGH -> HIGH (reinforced)

ADJUSTMENT: Trim NVDA 5% -> add to Broadcom (custom silicon for
inference-optimized chips is the new edge)
```

This is the power of session memory -- it knows what you were talking about, tracks how your thesis evolves, and grounds every claim in sources you can verify.

## Architecture

| Component | Purpose | Design Choice |
|-----------|---------|---------------|
| **Report Ingestion Tool** | Reads whitepapers, VC memos, 13F filings, earnings transcripts, geopolitical reports | PyMuPDF + unstructured for PDFs, SEC EDGAR API for 13Fs, web search for memos |
| **Web Search Tool** | Finds hidden reports, recent filings, institutional position changes | Tavily API (primary) + DuckDuckGo (fallback) |
| **Financial Data Tool** | Pulls real-time prices, fundamentals, peer comparison | yfinance + custom data sources |
| **Thesis Synthesizer** | Structures raw intelligence into conviction-grade investment thesis | LLM with strict Pydantic output schema |
| **Session Memory** | Persists thesis evolution, conviction changes, follow-up context | In-memory Pydantic state machine |
| **Orchestrator** | Decides plan -> tool call -> observe -> synthesize loop | Explicit state machine, no black-box agent loops |

## Session Memory

Across the conversation, finquill tracks:
- **Active theses** and their evolution (v1 -> v2 -> v3)
- **Conviction trajectory** (High -> Medium -> High, with reasoning)
- **Source inventory** (every report, filing, transcript referenced)
- **Open questions** (risks flagged but not yet resolved)
- **Position map** (if allocation suggested, track theoretical P&L)

This lets you pick up a thread from last week: *"Whatever happened to that India datacenter thesis?"* -- and finquill knows exactly which reports were read, what the conviction was, and what new data has emerged since.

## Project Structure

```
finquill/
  README.md                    # This file
  requirements.txt
  .env.example
  src/
    __init__.py
    agent.py                   # Main orchestrator
    tools/
      __init__.py
      report_ingestor.py       # PDF/whitepaper/13F ingestion
      web_search.py            # Hidden reports, filings, memos
      financial_data.py        # Prices, fundamentals, peers
      thesis_builder.py        # Structured thesis synthesis
    memory/
      __init__.py
      session.py               # Thesis evolution + conviction tracking
    models/
      __init__.py
      schemas.py               # Pydantic: Thesis, Position, SessionState
  eval/
    test_cases.json            # 20+ real-world prompts
    run_eval.py                # Eval runner
    metrics.py                 # Task completion, hallucination, coherence
  docs/
    architecture.md            # ADR: why raw Python, tool choices
  tests/
    test_agent.py              # Tool reliability + graceful failure
```

## Getting Started

```bash
# Clone
git clone https://github.com/prateekjain98/finquill.git
cd finquill

# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API keys:
#   - OPENAI_API_KEY (or GROQ_KEY for faster inference)
#   - TAVILY_API_KEY (for institutional-grade search)

# Run a thesis
python src/agent.py \
  "Leopold's AI infrastructure thesis -- what's the trade?" \
  --ticker NVDA

# Follow-up (uses session memory)
python src/agent.py \
  "What about the power bottleneck specifically?" \
  --session <session_id_from_previous>
```

## Why Raw Python (Not LangChain/CrewAI)

See docs/architecture.md for the full ADR. The short version:

- **Transparency**: Evaluators (and you) should understand the agent in 10 minutes. No framework magic.
- **Control**: Explicit plan -> tool -> observe -> synthesize loop. No black-box "agent" abstraction.
- **Reliability**: Structured Pydantic outputs on every LLM call. No free-text parsing that breaks at 2am.
- **Debuggability**: Every step is logged. When a thesis is wrong, you know exactly which tool output led it astray.

## Inspiration & Sources

- [Situational Awareness](https://situational-awareness.ai/) -- Leopold Aschenbrenner (June 2024)
- [Situational Awareness, Two Years Later](https://medium.com/data-science-collective/situational-awareness-two-years-later-4b941d052ef9) -- Omer Ansari (April 2026)
- [Leopold's $1.5B Hedge Fund](https://fortune.com/2025/10/08/leopold-aschenbrenner-openai-ftx-1-5-billion-hedge-fund-situational-awareness/) -- Fortune (Oct 2025)

## License

MIT
