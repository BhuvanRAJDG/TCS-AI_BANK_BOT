"""
app/rag/retriever.py
Retrieves relevant document chunks from ChromaDB.
Routes query to the correct collection based on keywords.
Returns top-K results with source citations.
"""
from __future__ import annotations
import logging
from typing import Optional

from .chroma_client import get_collection, is_available

log = logging.getLogger(__name__)

# ── Keyword → collection routing ──────────────────────────────────────────────
_ROUTING_RULES: list[tuple[set, str]] = [
    ({"rbi", "repo rate", "regulation", "circular", "guideline", "compliance",
      "rbi rule", "rbi policy", "reserve bank", "mandate", "eblr"}, "rbi_guidelines"),
    ({"insurance", "policy", "premium", "coverage", "claim", "hlpp", "health cover",
      "accidental", "term plan", "sum assured"}, "insurance_policies"),
    ({"loan", "home loan", "personal loan", "car loan", "education loan", "emi rate",
      "interest rate loan", "lender", "collateral", "processing fee"}, "loan_policies"),
]
_DEFAULT_COLLECTION = "faqs"

TOP_K = 3


def _route_query(query: str) -> str:
    q_lower = query.lower()
    for keywords, collection in _ROUTING_RULES:
        if any(kw in q_lower for kw in keywords):
            return collection
    return _DEFAULT_COLLECTION


def retrieve(query: str, collection_name: Optional[str] = None,
             top_k: int = TOP_K) -> dict:
    """
    Search ChromaDB for relevant chunks.
    Returns:
        {
          'context': str,          # concatenated text for the prompt
          'citations': list[str],  # source labels for the UI
          'collection': str,       # which collection was queried
          'available': bool        # False if ChromaDB not installed
        }
    """
    if not is_available():
        return {
            "context":    "",
            "citations":  [],
            "collection": collection_name or "unavailable",
            "available":  False,
        }

    col_name = collection_name or _route_query(query)
    col      = get_collection(col_name)

    if col is None:
        return {"context": "", "citations": [], "collection": col_name, "available": False}

    try:
        results = col.query(
            query_texts=[query],
            n_results=min(top_k, col.count() or 1),
        )
    except Exception as exc:
        log.error("ChromaDB query error: %s", exc)
        return {"context": "", "citations": [], "collection": col_name, "available": False}

    docs   = results.get("documents", [[]])[0]
    metas  = results.get("metadatas", [[]])[0]

    context   = "\n\n".join(f"[{i+1}] {d}" for i, d in enumerate(docs))
    citations = list({m.get("source", col_name) for m in metas})

    return {
        "context":    context,
        "citations":  citations,
        "collection": col_name,
        "available":  True,
    }
