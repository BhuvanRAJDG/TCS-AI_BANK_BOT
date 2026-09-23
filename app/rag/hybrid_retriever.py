"""
app/rag/hybrid_retriever.py
Advanced High-Performance Hybrid RAG Search Engine.
"""
import re
import math
import logging
from typing import Optional, List, Dict
from app.rag.ingest import SEED_DOCS
from app.rag.chroma_client import get_collection, is_available
from app.rag.learning_engine import get_user_learned_knowledge

log = logging.getLogger(__name__)

DOMAIN_SYNONYMS: dict[str, list[str]] = {
    "fd": ["fixed deposit", "term deposit", "interest rate", "fixed return", "apy"],
    "rd": ["recurring deposit", "monthly savings scheme"],
    "upi": ["fastpay upi", "instant transfer", "upi pin", "transaction limit", "qr code"],
    "emi": ["installment", "equated monthly installment", "loan repayment", "due date"],
    "cibil": ["credit score", "credit rating", "credit report", "credit bureau"],
    "foreclosure": ["prepayment", "loan closure penalty", "pre-closure", "early payoff"],
    "kyc": ["know your customer", "aadhaar verification", "pan card", "customer due diligence"],
    "hlpp": ["home loan protection plan", "home loan insurance", "mortgage insurance"],
    "rbi": ["reserve bank of india", "repo rate", "eblr", "circular", "monetary policy"],
    "card": ["debit card", "credit card", "atm card", "block card", "activate card"],
    "transfer": ["send money", "remit", "neft", "rtgs", "fastpay upi"],
    "timing": ["working hours", "branch timing", "open hours", "saturday banking"],
}

_ROUTING_RULES: list[tuple[set, str]] = [
    ({"rbi", "repo rate", "regulation", "circular", "guideline", "compliance",
      "rbi rule", "rbi policy", "reserve bank", "mandate", "eblr"}, "rbi_guidelines"),
    ({"insurance", "policy", "premium", "coverage", "claim", "hlpp", "health cover",
      "accidental", "term plan", "sum assured"}, "insurance_policies"),
    ({"loan", "home loan", "personal loan", "car loan", "education loan", "emi rate",
      "interest rate loan", "lender", "collateral", "processing fee"}, "loan_policies"),
]


def _route_query(query: str) -> str:
    q_lower = query.lower()
    for keywords, collection in _ROUTING_RULES:
        if any(kw in q_lower for kw in keywords):
            return collection
    return "faqs"


def expand_query(query: str) -> str:
    tokens = re.findall(r"\b[a-zA-Z0-9]+\b", query.lower())
    expansions = []
    for token in tokens:
        if token in DOMAIN_SYNONYMS:
            expansions.extend(DOMAIN_SYNONYMS[token][:3])

    if expansions:
        return f"{query} ({' '.join(expansions)})"
    return query


class BM25Searcher:
    def __init__(self):
        self.corpus: list[dict] = []
        for cat, doc_list in SEED_DOCS.items():
            for d in doc_list:
                self.corpus.append({
                    "id": d["id"],
                    "text": d["text"],
                    "source": d.get("source", cat.title()),
                    "category": cat
                })

    def search(self, query: str, top_k: int = 4) -> list[dict]:
        query_terms = re.findall(r"\b[a-zA-Z0-9]{2,}\b", query.lower())
        if not query_terms:
            return []

        scores = []
        for doc in self.corpus:
            doc_text = doc["text"].lower()
            score = 0.0
            for term in query_terms:
                count = doc_text.count(term)
                if count > 0:
                    term_len_boost = 1.0 + (len(term) / 10.0)
                    score += (count / (count + 1.5)) * term_len_boost * 2.0

            if score > 0:
                scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [{"text": d["text"], "source": d["source"], "score": round(s, 3)} for s, d in scores[:top_k]]


_bm25_searcher = BM25Searcher()


def hybrid_retrieve(query: str, user_id: Optional[int] = None, top_k: int = 3) -> dict:
    expanded_q = expand_query(query)
    citations = []
    context_chunks = []

    # 1. User Learned Memory (Highest Priority)
    learned_memories = get_user_learned_knowledge(user_id, query)
    top_learned = [m for m in learned_memories if m["relevance"] > 1][:2]

    for m in top_learned:
        context_chunks.append(f"[Learned Custom Fact] {m['topic']}: {m['content']}")
        citations.append(m['source'])

    # 2. ChromaDB Semantic Search
    chroma_results = []
    if is_available():
        try:
            col_name = _route_query(query)
            col = get_collection(col_name)
            if col and (col.count() or 0) > 0:
                q_res = col.query(query_texts=[expanded_q], n_results=top_k)
                docs = q_res.get("documents", [[]])[0]
                metas = q_res.get("metadatas", [[]])[0]
                for doc, meta in zip(docs, metas):
                    chroma_results.append({
                        "text": doc,
                        "source": meta.get("source", col_name.title())
                    })
        except Exception as exc:
            log.warning("ChromaDB query in hybrid retriever failed: %s", exc)

    # 3. BM25 Keyword Search
    bm25_results = _bm25_searcher.search(expanded_q, top_k=top_k)

    # 4. Merge & Deduplicate
    seen_texts = set()
    all_chunks = chroma_results + bm25_results

    for chunk in all_chunks:
        snippet = chunk["text"].strip()
        if snippet[:50] not in seen_texts and len(context_chunks) < (top_k + len(top_learned)):
            seen_texts.add(snippet[:50])
            context_chunks.append(snippet)
            if chunk["source"] not in citations:
                citations.append(chunk["source"])

    formatted_context = "\n\n".join(f"• {c}" for c in context_chunks)

    return {
        "context": formatted_context,
        "citations": citations[:4],
        "has_learned_memory": len(top_learned) > 0,
        "expanded_query": expanded_q
    }