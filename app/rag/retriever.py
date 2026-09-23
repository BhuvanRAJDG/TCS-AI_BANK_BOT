"""
app/rag/retriever.py
Standard gateway for hybrid retrieval.
"""
from app.rag.hybrid_retriever import hybrid_retrieve, _route_query


def retrieve(query: str, user_id=None, collection_name=None, top_k=3) -> dict:
    result = hybrid_retrieve(query=query, user_id=user_id, top_k=top_k)
    return {
        "context":    result["context"],
        "citations":  result["citations"],
        "collection": collection_name or "hybrid_knowledge",
        "available":  True,
    }