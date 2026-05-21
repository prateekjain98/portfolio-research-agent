# Evaluation Suite

The eval suite tests the agent on three dimensions from the brief:
1. **Task completion rate** — Does the agent produce a valid thesis with scored stocks?
2. **Hallucination on tool outputs** — Are claims grounded in retrieved documents?
3. **Graceful failure handling** — Does the agent degrade cleanly when tools fail?

---

## Test Cases

8 test cases cover core capabilities and edge cases:

| ID | Name | Prompt | Validates |
|---|---|---|---|
| tc-01 | Simple ticker query | `"Thesis on NVDA"` | Tool use: financial data + web search |
| tc-02 | Thematic query | `"Investment thesis on AI infrastructure"` | Document discovery path |
| tc-03 | Follow-up | `"What are the key risks?"` (after NVDA thesis) | Session memory recall |
| tc-04 | Ambiguous prompt | `"Is this a good buy?"` | Graceful degradation |
| tc-05 | Bad ticker | `"Thesis on XYZFAKE123"` | Tool failure handling |
| tc-06 | International | `"Thesis on Reliance Industries"` | Non-US ticker support |
| tc-07 | Multi-turn compare | `"Compare that to AMD"` (after NVDA) | Comparison across history |
| tc-08 | No results | `"Thesis on obscure private company"` | Empty corpus handling |

---

## Metrics

Metrics are split into three layers:

### Layer 1 — Component Metrics

| Metric | How it's computed |
|---|---|
| Document discovery | `1.0` if ≥1 valid PDF selected, else `0.0` |
| Document quality | Average score of selected documents |
| Tool use accuracy | Fraction of expected tools actually called |
| Error recovery | `1.0` no errors; `0.5` errors but thesis generated; `0.0` pipeline killed |

### Layer 2 — RAG Pipeline Metrics

| Metric | How it's computed |
|---|---|
| Retrieval precision@k | Fraction of retrieved chunks containing query keywords |
| Retrieval recall | Documents represented in chunks / total selected documents |
| Faithfulness | Supported claims / total verifiable claims (claims are sentences with numbers or tickers) |
| Answer relevancy | Keyword overlap between query and thesis |

### Layer 3 — End-to-End Metrics

| Metric | How it's computed |
|---|---|
| Task completion | `1.0` if thesis has theme header + stock recommendations |
| Thesis structure | Per-section checks: theme, rationale, risks, conviction, scores |
| Session memory | For follow-ups: `1.0` if response references previous context |
| Graceful degradation | `1.0` acknowledges limits + generates thesis; `0.5` generates without acknowledgment; `0.0` crashes |
| Hallucination rate | `1.0 - faithfulness` |

### Aggregate Score

Weighted average across all metrics:

| Metric | Weight |
|---|---|
| Task completion | 20% |
| Faithfulness | 20% |
| Tool use accuracy | 15% |
| Retrieval precision | 10% |
| Retrieval recall | 10% |
| Graceful degradation | 10% |
| Answer relevancy | 10% |
| Session memory | 5% |

Pass threshold: **≥ 70%**

---

## Running Evals

```bash
cd eval
python run_eval.py
```

Requires `BACKEND_URL` (defaults to `http://localhost:8000`) and a working LLM provider.

Output:
```
Results: 6/8 passed (75%)
Average score: 82%
Average duration: 12400ms
```

A JSON report is written to `eval/outputs/eval_{timestamp}.json`.

---

## Unit Tests

`tests/test_agent.py` tests tool reliability without requiring a live LLM:

| Test | What it checks |
|---|---|
| `test_web_search_returns_results` | Returns a list |
| `test_web_search_graceful_on_total_failure` | No crash on nonsense query |
| `test_stock_scorer_returns_partial_on_failure` | Fake ticker returns `None`, not exception |
| `test_stock_scorer_populates_known_ticker` | AAPL returns real yfinance data |
| `test_vector_store_lifecycle` | Index → query → delete works |
| `test_document_fetcher_finds_pdfs` | Finds, scores, downloads real PDFs |
| `test_document_fetcher_scoring` | Rankings are monotonic |

Run:
```bash
cd backend && pytest ../tests/test_agent.py -v
```
