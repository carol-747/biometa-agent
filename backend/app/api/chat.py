"""Conversational agent endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

from app.db.database import get_db
from app.services.agent import ConversationalAgent, get_or_create_session, save_session

router = APIRouter(prefix="/chat", tags=["chat"])

_agent: ConversationalAgent | None = None


def get_agent() -> ConversationalAgent:
    global _agent
    if _agent is None:
        _agent = ConversationalAgent()
    return _agent


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    relationships: list[dict]
    articles: list[dict]
    analysis: dict


@router.post("/", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    agent: ConversationalAgent = Depends(get_agent),
):
    """
    Send a message to the conversational agent.
    Supports natural language queries like:
    - "What metabolites does E. coli produce?"
    - "How does Lactobacillus regulate butyrate?"
    """
    session_id, history, _ = get_or_create_session(db, req.session_id)

    reply, updated_history, context = agent.chat(req.message, history, db)

    save_session(db, session_id, updated_history, context.get("analysis", {}))

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        relationships=context.get("relationships", []),
        articles=context.get("articles", []),
        analysis=context.get("analysis", {}),
    )


@router.delete("/{session_id}")
def clear_session(session_id: str, db: Session = Depends(get_db)):
    """Clear conversation history for a session."""
    from app.db.models import ConversationSession

    sess = db.query(ConversationSession).filter_by(session_id=session_id).first()
    if sess:
        sess.messages = []
        sess.context = {}
        db.commit()
    return {"status": "cleared", "session_id": session_id}


@router.get("/{session_id}/history")
def get_history(session_id: str, db: Session = Depends(get_db)):
    """Get conversation history for a session."""
    from app.db.models import ConversationSession

    sess = db.query(ConversationSession).filter_by(session_id=session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "messages": sess.messages}
