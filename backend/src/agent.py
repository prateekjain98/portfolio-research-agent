"""
Agent orchestrator.

First turn:  search -> fetch -> parse -> index -> retrieve -> synthesize -> score
Follow-up:   load history -> retrieve from existing index -> synthesize with context
"""

from __future__ import annotations

import asyncio
import json
import re
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


async def _llm_chat(client, messages, model, temperature, max_tokens):
    if isinstance(client, AsyncOpenAI):
        resp = await client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
            response_format={"type": "json_object"},
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
    resp = await client.messages.create(
        model=model,
        system=system_msg,
        messages=user_msgs,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.content[0].text if resp.content else "{}"
from src.db.supabase_client import get_supabase
from src.tools.document_fetcher import DocumentFetcher
from src.tools.document_parser import DocumentParser
from src.tools.stock_scorer import StockScorer
from src.tools.vector_store import SessionVectorStore
from src.tools.web_search import WebSearchTool


class Agent:
    def __init__(self) -> None:
        self.fetcher = DocumentFetcher()
        self.parser = DocumentParser()
        self.vector_store = SessionVectorStore()
        self.scorer = StockScorer()
        self.web_search = WebSearchTool()
        self.client = _get_llm_client()
        if settings.vertex_project:
            self.model = settings.vertex_model or "gemini-2.0-flash-001"
        elif settings.anthropic_api_key:
            self.model = settings.anthropic_model
        else:
            self.model = settings.llm_model
        self.db = get_supabase()

    async def run(
        self, query: str, session_id: Optional[str] = None, history: Optional[List[dict]] = None
    ) -> AsyncIterator[str]:
        history = history or []
        is_followup = False
        existing_docs = []

        # --- Load or create session -----------------------------------------
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
                session_id = None

        if session_id is None:
            session_id = str(uuid.uuid4())
            await asyncio.to_thread(
                self.db.table("thesis_sessions").insert({"id": session_id, "user_query": query}).execute
            )

        await asyncio.to_thread(
            self.db.table("messages").insert({"session_id": session_id, "role": "user", "content": query}).execute
        )

        yield f"**Thesis ID:** `{session_id[:8]}`\n\n"

        # --- First turn: discover documents ---------------------------------
        if not is_followup or not existing_docs:
            yield "**Searching** for reports...\n\n"
            docs = await asyncio.to_thread(self.fetcher.find_and_download, query, top_n=5)

            if not docs:
                yield "No good PDFs found. Using web snippets.\n\n"
            else:
                for d in docs:
                    yield f"- [{d['title']}]({d['url']}) (score: {d.get('score', 0):.2f})\n"
                yield "\n"

            yield "**Parsing**...\n\n"
            texts = []
            for d in docs:
                text = await asyncio.to_thread(self.parser.parse, d["path"])
                if text:
                    texts.append(text)
                    await asyncio.to_thread(
                        self.db.table("documents").insert({
                            "thesis_id": session_id,
                            "url": d["url"],
                            "title": d["title"],
                            "parsed_content": text[:2000],
                        }).execute
                    )
                    yield f"- [{d['title']}]({d['url']}): {len(text)} chars\n"
                else:
                    yield f"- Failed: [{d['title']}]({d['url']})\n"
            yield "\n"

            if texts:
                yield "**Indexing**...\n\n"
                n = await asyncio.to_thread(self.vector_store.index_documents, session_id, texts)
                yield f"- {n} chunks indexed\n\n"

        else:
            yield f"**Follow-up.** {len(existing_docs)} docs already indexed.\n\n"

        # --- Retrieve context -----------------------------------------------
        yield "**Retrieving** relevant passages...\n\n"

        retrieval_query = query
        if is_followup and len(history) >= 2:
            recent = history[-4:]
            retrieval_query = " | ".join(f"{m['role']}: {m['content'][:100]}" for m in recent)
            retrieval_query += f" | now: {query}"

        chunks = await asyncio.to_thread(self.vector_store.query, session_id, retrieval_query, top_k=8)
        if not chunks:
            web = await asyncio.to_thread(self.web_search.run, query, max_results=5)
            chunks = [f"{r.title}: {r.snippet}" for r in web]

        for i, c in enumerate(chunks[:4], 1):
            yield f"{i}. {c[:120].replace(chr(10), ' ')}...\n"
        yield "\n"

        context = "\n\n".join(chunks)

        # --- LLM synthesis --------------------------------------------------
        yield "**Analyzing**...\n\n"

        system_msg = (
            "You are a senior equity research analyst. "
            "Return ONLY valid JSON:\n"
            '{"theme":"...","summary":"...","conviction":"High|Medium|Low","stocks":['
            '{"ticker":"AAPL","name":"Apple Inc","rationale":"...","thematic_fit_score":85}]}'
        )

        messages = [{"role": "system", "content": system_msg}]
        if is_followup and history:
            for m in history[-6:]:
                if m.get("role") == "user":
                    messages.append({"role": "user", "content": m["content"]})
        else:
            messages.append({"role": "user", "content": query})

        messages.append({
            "role": "user",
            "content": f"Question: {query}\n\nResearch context:\n{context[:6000]}",
        })

        try:
            raw = await _llm_chat(self.client, messages, self.model, temperature=0.3, max_tokens=2000)
            # Extract JSON from markdown fences or plain text preamble
            json_match = re.search(r'```json\s*(\{.*\})\s*```', raw, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', raw, re.DOTALL)
                json_str = json_match.group(1) if json_match else raw
            parsed = json.loads(json_str)
        except Exception as e:
            yield f"LLM error: {e}\n\n"
            parsed = {"theme": query, "summary": "", "conviction": "Medium", "stocks": []}

        # --- Save thesis & score stocks -------------------------------------
        await asyncio.to_thread(
            self.db.table("thesis_sessions").update({
                "theme": parsed.get("theme", query),
                "summary": parsed.get("summary", ""),
                "conviction": parsed.get("conviction", "Medium"),
            }).eq("id", session_id).execute
        )

        stocks = parsed.get("stocks", [])
        scored = []
        for s in stocks:
            ticker = s.get("ticker", "")
            if not ticker:
                continue
            yield f"**Scoring** {ticker}...\n"
            sr = await asyncio.to_thread(self.scorer.score, ticker)
            m = sr["metrics"]
            fit = s.get("thematic_fit_score", 50)
            total = round(
                sr["fundamentals_score"] * 0.30 + fit * 0.25 + sr["risk_score"] * 0.20
                + sr["momentum_score"] * 0.15 + sr["liquidity_score"] * 0.10, 1
            )
            await asyncio.to_thread(
                self.db.table("stock_recommendations").insert({
                    "thesis_id": session_id,
                    "ticker": ticker,
                    "name": s.get("name"),
                    "entry_price": m.current_price,
                    "fundamentals_score": sr["fundamentals_score"],
                    "thematic_fit_score": fit,
                    "risk_score": sr["risk_score"],
                    "momentum_score": sr["momentum_score"],
                    "liquidity_score": sr["liquidity_score"],
                    "total_score": total,
                    "rationale": s.get("rationale"),
                }).execute
            )
            scored.append({
                "ticker": ticker, "name": s.get("name", ticker), "rationale": s.get("rationale", ""),
                "entry": m.current_price, "fundamentals": sr["fundamentals_score"],
                "thematic_fit": fit, "risk": sr["risk_score"], "momentum": sr["momentum_score"],
                "liquidity": sr["liquidity_score"], "total": total,
            })

        text = self._format(parsed, scored)
        await asyncio.to_thread(
            self.db.table("messages").insert({
                "session_id": session_id, "role": "assistant", "content": text
            }).execute
        )
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
        lines.append("---")
        lines.append("*Scores from real financial data + document analysis.*")
        lines.append("")
        return "\n".join(lines)
