"""
Agent orchestrator.

First turn:  search -> fetch -> parse -> index -> retrieve -> synthesize -> score
Follow-up:   load history -> retrieve from existing index -> synthesize with context
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from typing import AsyncIterator, List, Optional

from openai import AsyncOpenAI

from src.config import settings


def _get_llm_client():
    if settings.vertex_project:
        return "vertex"
    if settings.anthropic_api_key:
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=settings.anthropic_api_key)
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)


async def _llm_chat(client, messages, model, temperature, max_tokens, timeout_sec: float = 60.0):
    """Call LLM with timeout. Raises asyncio.TimeoutError if exceeded."""
    if isinstance(client, AsyncOpenAI):
        resp = await asyncio.wait_for(
            client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"},
            ),
            timeout=timeout_sec,
        )
        return resp.choices[0].message.content or "{}"
    if client == "vertex":
        from google import genai
        from google.genai import types
        gemini = genai.Client(vertexai=True, project=settings.vertex_project, location=settings.vertex_location or "us-central1")
        system_msg = ""
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            elif m["role"] == "user":
                user_msgs.append(types.Content(role="user", parts=[types.Part(text=m["content"])]))
            elif m["role"] == "assistant":
                user_msgs.append(types.Content(role="model", parts=[types.Part(text=m["content"])]))
        config = types.GenerateContentConfig(system_instruction=system_msg, temperature=temperature, max_output_tokens=max_tokens)
        resp = gemini.models.generate_content(model=model, contents=user_msgs, config=config)
        return resp.text or "{}"
    # Anthropic
    system_msg = ""
    user_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            user_msgs.append({"role": m["role"], "content": m["content"]})
    resp = await asyncio.wait_for(
        client.messages.create(
            model=model,
            system=system_msg,
            messages=user_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        ),
        timeout=timeout_sec,
    )
    return resp.content[0].text if resp.content else "{}"
from src.db.supabase_client import get_supabase
from src.tools.document_fetcher import DocumentFetcher
from src.tools.document_parser import DocumentParser
from src.tools.stock_scorer import StockScorer
from src.tools.vector_store import SessionVectorStore
from src.tools.web_search import WebSearchTool
from src.tools.theme_mapper import ThemeMapper


class Agent:
    def __init__(self) -> None:
        self.fetcher = DocumentFetcher()
        self.parser = DocumentParser()
        self.vector_store = SessionVectorStore()
        self.scorer = StockScorer()
        self.web_search = WebSearchTool()
        self.theme_mapper = ThemeMapper()
        self.client = _get_llm_client()
        if settings.vertex_project:
            self.model = settings.vertex_model or "gemini-2.0-flash-001"
        elif settings.anthropic_api_key:
            self.model = settings.anthropic_model
        else:
            self.model = settings.llm_model
        self.db = get_supabase()

    async def run(
        self, query: str, session_id: Optional[str] = None, history: Optional[List[dict]] = None, model: Optional[str] = None
    ) -> AsyncIterator[str]:
        start_time = time.time()
        history = history or []
        is_followup = False
        existing_docs = []
        raw_data: dict = {"query": query, "documents": [], "chunks": [], "stocks": []}

        # Use requested model if provided and valid
        active_model = model if model else self.model

        # Total pipeline timeout: if we exceed this, return partial results
        PIPELINE_TIMEOUT = 75.0

        # Validate session_id format (must be a valid UUID)
        _UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
        if session_id and not _UUID_RE.match(session_id):
            print(f"[Agent] Invalid session_id format: {session_id!r}, treating as None")
            session_id = None

        # --- Load or create session -----------------------------------------
        try:
            if session_id:
                resp = await asyncio.to_thread(
                    self.db.table("thesis_sessions").select("*").eq("id", session_id).execute
                )
                if resp.data:
                    is_followup = True
                    docs_resp = await asyncio.to_thread(
                        self.db.table("documents").select("*").eq("thesis_id", session_id).execute
                    )
                    existing_docs = docs_resp.data or []
                else:
                    yield "Session not found. Starting a new thesis.\n\n"
                    # Keep the provided session_id so follow-ups use the same ID

            if not is_followup:
                # Create new session (use provided id if valid, else generate one)
                if not session_id:
                    session_id = str(uuid.uuid4())
                await asyncio.to_thread(
                    self.db.table("thesis_sessions").insert({"id": session_id, "user_query": query}).execute
                )

            await asyncio.to_thread(
                self.db.table("messages").insert({"session_id": session_id, "role": "user", "content": query}).execute
            )
        except Exception as e:
            print(f"[Agent] DB error during session setup: {e}")
            # If DB ops failed, ensure we have a valid session_id to continue
            if not session_id:
                session_id = str(uuid.uuid4())

        if not session_id:
            session_id = str(uuid.uuid4())

        yield f"**Thesis ID:** `{session_id}`\n\n"

        # --- First turn: discover documents ---------------------------------
        docs = []
        if not is_followup or not existing_docs:
            yield "**Searching** for reports...\n\n"
            t0 = time.time()
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(self.fetcher.find_and_download, query, top_n=5),
                    timeout=35.0,
                )
            except asyncio.TimeoutError:
                print(f"[Agent] Discovery timed out after 35s, proceeding with web snippets")
                yield "Document search timed out. Using web snippets.\n\n"
            print(f"[Agent] Discovery took {time.time()-t0:.1f}s, found {len(docs)} docs")

            if not docs:
                yield "No good PDFs found. Using web snippets.\n\n"
            else:
                for d in docs:
                    yield f"- [{d['title']}]({d['url']}) (score: {d.get('score', 0):.2f})\n"
                yield "\n"

            yield "**Parsing**...\n\n"
            t0 = time.time()
            texts = []
            for d in docs:
                text = await asyncio.to_thread(self.parser.parse, d["path"])
                if text:
                    texts.append(text)
                    try:
                        await asyncio.to_thread(
                            self.db.table("documents").insert({
                                "thesis_id": session_id,
                                "url": d["url"],
                                "title": d["title"],
                                "parsed_content": text[:2000],
                            }).execute
                        )
                    except Exception as e:
                        print(f"[Agent] DB error saving document: {e}")
                    yield f"- [{d['title']}]({d['url']}): {len(text)} chars\n"
                else:
                    yield f"- Failed: [{d['title']}]({d['url']})\n"
            yield "\n"

            if texts:
                yield "**Indexing**...\n\n"
                n = await asyncio.to_thread(self.vector_store.index_documents, session_id, texts)
                print(f"[Agent] Indexed {n} chunks in {time.time()-t0:.1f}s")
                yield f"- {n} chunks indexed\n\n"
            for d in docs:
                raw_data["documents"].append({"url": d["url"], "title": d["title"], "score": d.get("score", 0)})

        else:
            yield f"**Follow-up.** {len(existing_docs)} docs already indexed.\n\n"

        # --- Retrieve context -----------------------------------------------
        yield "**Retrieving** relevant passages...\n\n"

        retrieval_query = query
        if is_followup and len(history) >= 2:
            recent = history[-4:]
            retrieval_query = " | ".join(f"{m['role']}: {m['content'][:100]}" for m in recent)
            retrieval_query += f" | now: {query}"

        chunks = await asyncio.to_thread(self.vector_store.query, session_id, retrieval_query, top_k=12)
        print(f"[Agent] Retrieved {len(chunks)} chunks")
        raw_data["chunks"] = chunks[:4]
        if not chunks:
            web = await asyncio.to_thread(self.web_search.run, query, max_results=5)
            chunks = [f"{r.title}: {r.snippet}" for r in web]
            raw_data["chunks"] = chunks[:4]

        for i, c in enumerate(chunks[:4], 1):
            yield f"{i}. {c[:120].replace(chr(10), ' ')}...\n"
        yield "\n"

        context = "\n\n".join(chunks)

        # --- Augment follow-up context with fresh web search ----------------
        if is_followup:
            yield "**Searching** for fresh data on your follow-up...\n\n"
            try:
                web_results = await asyncio.to_thread(self.web_search.run, query, max_results=5)
                fresh_chunks = [f"{r.title}: {r.snippet}" for r in web_results]
                if fresh_chunks:
                    yield f"- Found {len(fresh_chunks)} fresh sources\n\n"
                    context += "\n\n--- FRESH FOLLOW-UP RESEARCH ---\n\n" + "\n\n".join(fresh_chunks)
            except Exception as e:
                print(f"[Agent] Follow-up web search error: {e}")

        # --- LLM synthesis --------------------------------------------------
        yield "**Analyzing**...\n\n"

        if is_followup:
            system_msg = (
                "You are a senior equity research analyst. This is a FOLLOW-UP question from the user "
                "about a previous investment thesis. Answer their question directly and thoroughly.\n\n"
                "CRITICAL RULES:\n"
                "1. If the user mentions a SPECIFIC stock or ticker (e.g., 'dive deeper into NVST'), "
                "   you MUST return ONLY that exact ticker in the stocks array. Provide deep analysis "
                "   on ONLY that stock: business model, financial health, competitive position, risks, "
                "   catalysts, and a clear buy/hold/sell stance. The rationale should be a detailed paragraph.\n"
                "2. If the user asks a GENERAL question (e.g., 'what are the risks?'), answer using the research context.\n"
                "3. NEVER include unrelated stocks or competitors unless the user explicitly asks for alternatives.\n"
                "4. The 'theme' field should summarize the user's specific question, not a broad sector.\n"
                "5. Be concise but thorough. Cite specific data points from the research context.\n\n"
                "Return ONLY valid JSON:\n"
                '{"theme":"Deep Dive: NVST","summary":" focused analysis...","conviction":"High|Medium|Low","stocks":['
                '{"ticker":"NVST","name":"Envista Holdings","rationale":"Detailed 200-word analysis on NVST covering business model, financials, risks, and catalysts...","thematic_fit_score":85}]}'
            )
        else:
            system_msg = (
                "You are a senior equity research analyst. Read the research context, "
                "extract key investment themes, and map each theme to specific public companies.\n\n"
                "STEP-BY-STEP PROCESS — you MUST follow these steps:\n"
                "1. List the KEY BOTTLENECKS or themes described in the research context.\n"
                "2. For EACH bottleneck, name 3-5 PUBLIC COMPANIES that are pure-plays or major beneficiaries. Aim for 5-7 total stocks.\n"
                "3. Explain the logical connection for each: 'Thesis says X → Company Y does Z → Y benefits.'\n"
                "4. AVOID generic giants (AAPL, GOOGL, MSFT, AMZN, META, TSLA). Prefer pure-plays.\n\n"
                "Return ONLY valid JSON:\n"
                '{"theme":"...","summary":"...","conviction":"High|Medium|Low","stocks":['
                '{"ticker":"BE","name":"Bloom Energy","rationale":"Thesis argues data centers need on-site fuel cells. BE manufactures solid-oxide fuel cells.","thematic_fit_score":95}]}'
            )

        messages = [{"role": "system", "content": system_msg}]
        if is_followup and history:
            # Include full conversation history so the LLM knows what was previously discussed
            for m in history[-6:]:
                role = m.get("role")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": m["content"]})

        messages.append({
            "role": "user",
            "content": f"Question: {query}\n\nResearch context:\n{context[:6000]}",
        })

        parsed = {"theme": query, "summary": "", "conviction": "Medium", "stocks": []}
        try:
            raw = await _llm_chat(self.client, messages, active_model, temperature=0.3, max_tokens=3000)
            # Extract JSON from markdown fences or plain text preamble
            json_match = re.search(r'```json\s*(\{.*\})\s*```', raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', raw, re.DOTALL)
                json_str = json_match.group(1) if json_match else raw
            parsed = json.loads(json_str)
            print(f"[Agent] LLM parsed: theme={parsed.get('theme')}, stocks={len(parsed.get('stocks', []))}")
        except Exception as e:
            print(f"[Agent] LLM JSON parse failed: {e}")
            try:
                print(f"[Agent] Raw LLM output (first 500 chars): {raw[:500]}")
            except:
                pass
            yield f"LLM error: {e}\n\n"

        # --- Save thesis & score stocks -------------------------------------
        try:
            await asyncio.to_thread(
                self.db.table("thesis_sessions").update({
                    "theme": parsed.get("theme", query),
                    "summary": parsed.get("summary", ""),
                    "conviction": parsed.get("conviction", "Medium"),
                }).eq("id", session_id).execute
            )
        except Exception as e:
            print(f"[Agent] DB error updating thesis: {e}")

        stocks = parsed.get("stocks", [])

        # --- ThemeMapper fallback -------------------------------------------
        # For first-turn: if LLM produced no stocks or only generic FAANG, use ThemeMapper.
        # For follow-ups: trust the LLM's focused output (often just 1 stock).
        if not is_followup:
            GENERIC_TICKERS = {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA", "GOOG"}
            llm_tickers = {s.get("ticker", "").upper() for s in stocks}
            if len(stocks) < 3 or llm_tickers.issubset(GENERIC_TICKERS):
                theme = parsed.get("theme", query)
                yield f"**Deep research** mapping '{theme}' to specific companies...\n\n"
                try:
                    mapped = await asyncio.to_thread(
                        self.theme_mapper.map_themes, [theme], max_results_per_theme=5
                    )
                    print(f"[Agent] ThemeMapper returned {len(mapped)} tickers: {[m['ticker'] for m in mapped]}")
                    for m in mapped:
                        if m["ticker"] not in llm_tickers:
                            stocks.append({
                                "ticker": m["ticker"],
                                "name": m["ticker"],
                                "rationale": f"Mapped from theme: {m['theme']}",
                                "thematic_fit_score": 75,
                            })
                except Exception as e:
                    print(f"[Agent] ThemeMapper error: {e}")

        print(f"[Agent] Scoring {len(stocks)} stocks")
        scored = []

        # Score stocks in parallel for speed
        async def _score_one(s: dict) -> dict:
            ticker = s.get("ticker", "")
            if not ticker:
                return None
            sr = await asyncio.to_thread(self.scorer.score, ticker)
            m = sr["metrics"]
            fit = s.get("thematic_fit_score", 50)
            total = round(
                sr["fundamentals_score"] * 0.30 + fit * 0.25 + sr["risk_score"] * 0.20
                + sr["momentum_score"] * 0.15 + sr["liquidity_score"] * 0.10, 1
            )
            return {
                "ticker": ticker, "name": s.get("name", ticker), "rationale": s.get("rationale", ""),
                "entry": m.current_price, "fundamentals": sr["fundamentals_score"],
                "thematic_fit": fit, "risk": sr["risk_score"], "momentum": sr["momentum_score"],
                "liquidity": sr["liquidity_score"], "total": total,
                "_sr": sr, "_fit": fit,
            }

        score_tasks = [_score_one(s) for s in stocks if s.get("ticker")]
        score_results = await asyncio.gather(*score_tasks, return_exceptions=True)

        for res in score_results:
            if isinstance(res, Exception):
                print(f"[Agent] Stock scoring error: {res}")
                continue
            if res is None:
                continue
            ticker = res["ticker"]
            sr = res.pop("_sr")
            fit = res.pop("_fit")
            try:
                await asyncio.to_thread(
                    self.db.table("stock_recommendations").insert({
                        "thesis_id": session_id,
                        "ticker": ticker,
                        "name": res["name"],
                        "entry_price": res["entry"],
                        "fundamentals_score": res["fundamentals"],
                        "thematic_fit_score": fit,
                        "risk_score": res["risk"],
                        "momentum_score": res["momentum"],
                        "liquidity_score": res["liquidity"],
                        "total_score": res["total"],
                        "rationale": res["rationale"],
                    }).execute
                )
            except Exception as e:
                print(f"[Agent] DB error saving stock {ticker}: {e}")
            scored.append(res)
            raw_data["stocks"].append({"ticker": ticker, "total_score": res["total"], **sr})

        elapsed = time.time() - start_time
        print(f"[Agent] Pipeline complete in {elapsed:.1f}s")

        if elapsed > PIPELINE_TIMEOUT:
            print(f"[Agent] WARNING: Pipeline exceeded {PIPELINE_TIMEOUT}s timeout")

        text = self._format(parsed, scored)
        try:
            await asyncio.to_thread(
                self.db.table("messages").insert({
                    "session_id": session_id, "role": "assistant", "content": text
                }).execute
            )
        except Exception as e:
            print(f"[Agent] DB error saving assistant message: {e}")
        yield text

    @staticmethod
    def _format(parsed: dict, stocks: List[dict]) -> str:
        lines = [
            f"## {parsed.get('theme', 'Investment Thesis')}",
            "",
            f"**Conviction:** {parsed.get('conviction', 'Medium')}",
            "",
            "### Executive Summary",
            parsed.get("summary", "No summary available."),
            "",
            "### Recommended Positions",
        ]
        for s in stocks:
            lines.append(f"- **{s['ticker']}** ({s['name']}) — Score: {s['total']}/100")
            if s["entry"]:
                lines.append(f"  - Entry: ${s['entry']:,.2f}")
            lines.append(
                f"  - F:{s['fundamentals']} T:{s['thematic_fit']} R:{s['risk']} "
                f"M:{s['momentum']} L:{s['liquidity']}"
            )
            lines.append(f"  - {s['rationale']}")
            lines.append("")
        if not stocks:
            lines.append("*No specific stocks were identified in the research corpus.*")
            lines.append("")
        lines.append("---")
        lines.append("*Scores from real financial data + document analysis.*")
        lines.append("")
        return "\n".join(lines)
