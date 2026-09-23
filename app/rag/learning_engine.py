"""
app/rag/learning_engine.py
Active conversational learning engine for CBS Bank Copilot.
"""
import re
import logging
from datetime import datetime
from typing import Optional, Tuple
from app import db
from app.models.user_knowledge import UserKnowledge

log = logging.getLogger(__name__)

LEARN_PATTERNS = [
    re.compile(r"^(?:please\s+)?(?:remember|note\s+down|keep\s+in\s+mind|note\s+that|learn\s+this|save\s+this\s+note|from\s+now\s+on)\s*(?:that|:|,)?\s*(.+)$", re.I),
    re.compile(r"^my\s+([a-zA-Z0-9\s]+?)\s+(?:is|are|will\s+be)\s+(.+)$", re.I),
    re.compile(r"^(?:update|add|new)\s+(?:faq|rule|policy|info|branch\s+timing):\s*(.+)$", re.I),
    re.compile(r"^i\s+prefer\s+(.+)$", re.I),
]


def extract_learning_fact(message: str) -> Optional[Tuple[str, str, str]]:
    msg = message.strip()
    if len(msg) < 8 or len(msg) > 600:
        return None

    for pat in LEARN_PATTERNS:
        m = pat.match(msg)
        if m:
            groups = m.groups()
            if len(groups) == 1:
                content = groups[0].strip()
                topic = "User Note / Instruction"
                if "branch" in content.lower():
                    topic = "Branch Preference / Timing"
                elif "email" in content.lower() or "phone" in content.lower():
                    topic = "Contact Preference"
                elif "tax" in content.lower() or "pan" in content.lower():
                    topic = "Tax & Compliance Preference"
                elif "bill" in content.lower() or "pay" in content.lower():
                    topic = "Payment Preference"
                return "preference", topic, content
            elif len(groups) >= 2:
                topic = groups[0].strip().title()
                content = groups[1].strip()
                return "preference", f"User {topic}", f"{topic} is {content}"

    return None


def store_learned_fact(user_id: Optional[int], category: str, topic: str, content: str) -> dict:
    clean_words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", f"{topic} {content}".lower())
    keywords = ",".join(sorted(list(set(clean_words))))

    existing = UserKnowledge.query.filter_by(user_id=user_id, topic=topic).first()
    if existing:
        existing.content = content
        existing.keywords = keywords
        existing.created_at = datetime.utcnow()
    else:
        entry = UserKnowledge(
            user_id=user_id,
            category=category,
            topic=topic,
            content=content,
            keywords=keywords,
            created_at=datetime.utcnow()
        )
        db.session.add(entry)

    db.session.commit()

    try:
        from app.rag.chroma_client import get_collection, is_available
        if is_available():
            col = get_collection("user_learned_knowledge")
            if col:
                doc_id = f"user_{user_id or 0}_{hash(topic)}"
                col.upsert(
                    ids=[doc_id],
                    documents=[f"{topic}: {content}"],
                    metadatas=[{"user_id": str(user_id or 0), "topic": topic, "source": "User Dynamic Memory"}]
                )
    except Exception as exc:
        log.warning("ChromaDB indexing for learned fact failed: %s", exc)

    return {
        "topic": topic,
        "content": content,
        "category": category
    }


def get_user_learned_knowledge(user_id: Optional[int], query: str = "") -> list[dict]:
    if not user_id:
        items = UserKnowledge.query.filter_by(user_id=None).all()
    else:
        items = UserKnowledge.query.filter(
            (UserKnowledge.user_id == user_id) | (UserKnowledge.user_id.is_(None))
        ).order_by(UserKnowledge.created_at.desc()).limit(15).all()

    results = []
    q_lower = query.lower()
    for item in items:
        relevance = 1
        if query:
            tokens = [t for t in item.keywords.split(',') if t] if item.keywords else []
            matches = sum(1 for t in tokens if t in q_lower)
            if matches > 0 or item.topic.lower() in q_lower:
                relevance += 5 + matches

        results.append({
            "id": item.id,
            "topic": item.topic,
            "content": item.content,
            "category": item.category,
            "relevance": relevance,
            "source": f"Learned Preference: {item.topic}"
        })

    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results