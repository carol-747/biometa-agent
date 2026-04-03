"""
Conversational agent powered by Anthropic Claude API.
Supports multi-turn dialogue with context maintenance.
Understands natural language queries about microbe-metabolite relationships.
"""
import json
import logging
import uuid
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.nlp.semantic_search import semantic_search
from app.nlp.entity_extractor import extract_entities

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are BiometaAgent, an expert AI assistant specializing in
microbe-metabolite relationships from scientific literature. You help researchers
discover how microorganisms (bacteria, fungi, viruses, archaea) interact with
metabolites (fatty acids, amino acids, secondary metabolites, etc.).

You have access to a database of PubMed articles with extracted entities and
relationships. When answering questions:
1. Interpret the user's query to identify microbes and metabolites of interest
2. Report findings with citations (PMID, journal, date)
3. Indicate confidence levels for each relationship
4. Suggest related queries when relevant
5. Maintain conversational context across turns

Respond in a clear, scientific but accessible tone. Format relationship findings as:
- [Microbe] → [relationship_type] → [Metabolite] (Confidence: X%, Source: PMID XXXXX)

When asked for visualization, explain the network structure in text form."""

QUERY_ANALYSIS_PROMPT = """Analyze this user query about microbe-metabolite relationships.
Extract:
1. microbes: list of microorganism names mentioned or implied
2. metabolites: list of metabolite names mentioned or implied
3. relationship_types: list of relationship types (produces, consumes, regulates, etc.)
4. search_query: best semantic search string for finding relevant articles

Return ONLY valid JSON with keys: microbes, metabolites, relationship_types, search_query

User query: {query}"""


class ConversationalAgent:
    """Stateless agent; conversation history passed in each call."""

    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"

    def _analyze_query(self, query: str) -> dict[str, Any]:
        """Use Claude to extract entities and intent from user query."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {
                        "role": "user",
                        "content": QUERY_ANALYSIS_PROMPT.format(query=query),
                    }
                ],
            )
            text = response.content[0].text.strip()
            # Extract JSON from potential markdown code block
            if "```" in text:
                text = text.split("```")[1].lstrip("json").strip()
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Query analysis failed: {e}")
            return {
                "microbes": [],
                "metabolites": [],
                "relationship_types": [],
                "search_query": query,
            }

    def _fetch_context(
        self,
        db: Session,
        analysis: dict[str, Any],
        original_query: str,
    ) -> dict[str, Any]:
        """Gather relevant articles and relationships from the database."""
        from app.db.models import (
            MicrobeMetaboliteRelationship,
            Microbe,
            Metabolite,
            Article,
        )
        from sqlalchemy import or_

        search_q = analysis.get("search_query", original_query)
        articles = semantic_search(db, search_q, top_k=10)

        # Fetch relationships matching extracted entities
        relationships = []
        microbe_names = [m.lower() for m in analysis.get("microbes", [])]
        metabolite_names = [m.lower() for m in analysis.get("metabolites", [])]

        if microbe_names or metabolite_names:
            q = db.query(MicrobeMetaboliteRelationship).join(
                Microbe, MicrobeMetaboliteRelationship.microbe_id == Microbe.id
            ).join(
                Metabolite, MicrobeMetaboliteRelationship.metabolite_id == Metabolite.id
            ).join(
                Article, MicrobeMetaboliteRelationship.article_id == Article.id
            )

            filters = []
            for name in microbe_names:
                filters.append(Microbe.name.ilike(f"%{name}%"))
            for name in metabolite_names:
                filters.append(Metabolite.name.ilike(f"%{name}%"))

            rels = q.filter(or_(*filters)).limit(30).all() if filters else []

            for rel in rels:
                relationships.append({
                    "microbe": rel.microbe.name,
                    "metabolite": rel.metabolite.name,
                    "relationship_type": rel.relationship_type,
                    "confidence": rel.confidence_score,
                    "evidence": rel.evidence_sentence,
                    "pmid": rel.article.pmid,
                    "journal": rel.article.journal,
                    "pub_date": rel.article.pub_date,
                })

        return {"articles": articles, "relationships": relationships}

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict],
        db: Session,
    ) -> tuple[str, list[dict], dict[str, Any]]:
        """
        Process a user message and return (reply, updated_history, context).
        conversation_history: list of {role, content} dicts
        """
        # Analyze query
        analysis = self._analyze_query(user_message)

        # Fetch database context
        db_context = self._fetch_context(db, analysis, user_message)

        # Build context injection
        context_text = self._format_context(db_context)

        # Build messages for Claude
        messages = list(conversation_history)
        messages.append(
            {
                "role": "user",
                "content": f"{user_message}\n\n[DATABASE CONTEXT]\n{context_text}",
            }
        )

        # If no API key configured, skip Claude and format results directly
        if not self.client.api_key:
            reply = self._format_direct_reply(user_message, db_context)
            updated_history = list(conversation_history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": reply})
            return reply, updated_history, {
                "analysis": analysis,
                "articles": db_context["articles"],
                "relationships": db_context["relationships"],
            }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            reply = response.content[0].text

            # Update history (store clean version without context injection)
            updated_history = list(conversation_history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": reply})

            return reply, updated_history, {
                "analysis": analysis,
                "articles": db_context["articles"],
                "relationships": db_context["relationships"],
            }

        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
            logger.warning("Claude API key invalid or missing — using direct DB fallback")
            reply = self._format_direct_reply(user_message, db_context)
            updated_history = list(conversation_history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": reply})
            return reply, updated_history, db_context

        except anthropic.RateLimitError:
            reply = (
                "Claude API rate limit reached. Here are the raw database results:\n\n"
                + self._format_context(db_context)
            )
            updated_history = list(conversation_history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": reply})
            return reply, updated_history, db_context

        except Exception as e:
            logger.error(f"Agent error: {e}")
            reply = self._format_direct_reply(user_message, db_context)
            updated_history = list(conversation_history)
            updated_history.append({"role": "user", "content": user_message})
            updated_history.append({"role": "assistant", "content": reply})
            return reply, updated_history, db_context

    def _format_direct_reply(self, query: str, ctx: dict[str, Any]) -> str:
        """
        Produce a structured plain-text reply from database results alone,
        used when the Claude API is unavailable.
        """
        lines = [f"**Database results for:** _{query}_\n"]

        rels = ctx.get("relationships", [])
        arts = ctx.get("articles", [])

        if rels:
            lines.append(f"**Relationships found ({len(rels)}):**\n")
            for r in rels[:15]:
                conf_pct = int((r.get("confidence") or 0) * 100)
                lines.append(
                    f"- **{r['microbe']}** → `{r['relationship_type']}` → **{r['metabolite']}**  "
                    f"(Confidence: {conf_pct}%, PMID: [{r['pmid']}]"
                    f"(https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/))"
                )
                if r.get("evidence"):
                    lines.append(f"  > _{r['evidence'][:200]}_")
        else:
            lines.append("No relationships found in the database for this query.")

        if arts:
            lines.append(f"\n**Relevant articles ({len(arts)}):**\n")
            for a in arts[:5]:
                link = a.get("full_text_link") or f"https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/"
                lines.append(
                    f"- [{a['title'][:100]}]({link})  "
                    f"_{a.get('journal', '')}_, {a.get('pub_date', '')} — "
                    f"score: {a.get('score', 0):.2f}"
                )

        if not rels and not arts:
            lines.append(
                "\nTip: Use the **Ingest** tab to fetch PubMed articles first, "
                "then ask your question again."
            )

        lines.append(
            "\n_Note: Claude API is not configured. "
            "Set ANTHROPIC_API_KEY in your .env for conversational responses._"
        )
        return "\n".join(lines)

    def _format_context(self, ctx: dict[str, Any]) -> str:
        """Format database context for injection into Claude prompt."""
        parts = []

        if ctx["relationships"]:
            parts.append("RELATIONSHIPS FOUND:")
            for r in ctx["relationships"][:15]:
                parts.append(
                    f"  {r['microbe']} --[{r['relationship_type']}]--> "
                    f"{r['metabolite']} "
                    f"(confidence: {r['confidence']:.2f}, "
                    f"PMID: {r['pmid']}, {r['journal']}, {r['pub_date']})"
                )
                if r.get("evidence"):
                    parts.append(f"    Evidence: {r['evidence'][:200]}")

        if ctx["articles"]:
            parts.append("\nRELEVANT ARTICLES:")
            for a in ctx["articles"][:5]:
                parts.append(
                    f"  [{a['pmid']}] {a['title'][:100]} "
                    f"({a['journal']}, {a['pub_date']}) score={a['score']:.3f}"
                )

        if not parts:
            parts.append("No specific database matches found for this query.")

        return "\n".join(parts)


def get_or_create_session(db: Session, session_id: str | None) -> tuple[str, list, dict]:
    """Load or create a conversation session from the database."""
    from app.db.models import ConversationSession

    if session_id:
        sess = db.query(ConversationSession).filter_by(session_id=session_id).first()
        if sess:
            return sess.session_id, sess.messages or [], sess.context or {}

    new_id = session_id or str(uuid.uuid4())
    sess = ConversationSession(session_id=new_id, messages=[], context={})
    db.add(sess)
    db.commit()
    return new_id, [], {}


def save_session(db: Session, session_id: str, messages: list, context: dict):
    """Persist updated conversation session."""
    from app.db.models import ConversationSession

    sess = db.query(ConversationSession).filter_by(session_id=session_id).first()
    if sess:
        sess.messages = messages
        sess.context = context
        db.commit()
