"""
app/rag/chroma_client.py
Singleton ChromaDB client with lazy initialization.
Falls back gracefully if chromadb is not installed.
"""
from __future__ import annotations
import os
import logging

log = logging.getLogger(__name__)

_client      = None
_collections = {}

COLLECTIONS = ["faqs", "rbi_guidelines", "loan_policies", "insurance_policies"]


def get_client():
    """Return (or create) the singleton ChromaDB client."""
    global _client
    if _client is not None:
        return _client
    try:
        import chromadb
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        os.makedirs(persist_dir, exist_ok=True)
        _client = chromadb.PersistentClient(path=persist_dir)
        log.info("ChromaDB client initialized at %s", persist_dir)
    except ImportError:
        log.warning("chromadb not installed — RAG disabled. pip install chromadb")
        _client = None
    except Exception as exc:
        log.error("ChromaDB init failed: %s", exc)
        _client = None
    return _client


def get_collection(name: str):
    """Get or create a named collection."""
    if name in _collections:
        return _collections[name]
    client = get_client()
    if client is None:
        return None
    try:
        col = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
        _collections[name] = col
        return col
    except Exception as exc:
        log.error("Failed to get collection %s: %s", name, exc)
        return None


def is_available() -> bool:
    return get_client() is not None
