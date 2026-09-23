"""
app/services/ai_chat_service.py
Thin service layer over the AI orchestrator.
Manages per-user in-memory conversation history.
"""
from __future__ import annotations
import threading
from typing import Optional
from app.ai.orchestrator import process_query

_LOCK    = threading.Lock()
_HISTORY: dict[int, list[dict]] = {}
MAX_HISTORY_TURNS = 20


def get_history(user_id: int) -> list[dict]:
    with _LOCK:
        return list(_HISTORY.get(user_id, []))


def _append_history(user_id: int, role: str, content: str) -> None:
    with _LOCK:
        history = _HISTORY.setdefault(user_id, [])
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY_TURNS:
            _HISTORY[user_id] = history[-MAX_HISTORY_TURNS:]


def clear_history(user_id: int) -> None:
    with _LOCK:
        _HISTORY.pop(user_id, None)


def chat(message: str, user_id: int, customer_id: Optional[int] = None) -> dict:
    history = get_history(user_id)

    result = process_query(
        query=message,
        customer_id=customer_id,
        history=history,
        user_id=user_id,
    )

    if result.get("intent") != "blocked":
        _append_history(user_id, "user", message)
        _append_history(user_id, "assistant", result["response"])

    return result