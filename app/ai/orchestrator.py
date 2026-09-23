"""
app/ai/orchestrator.py
Minimal AI Banking Copilot pipeline.

Route A — SQL intents (balance, transactions, emi, loans, credit_score)
    → fetch structured data from MySQL
    → build prompt with real account data
    → call GPT-4o

Route B — Document intents (faq, rbi, loan_info, insurance)
    → retrieve from ChromaDB
    → build prompt with context chunks
    → call GPT-4o
"""
from __future__ import annotations
import os
import re
import time
import logging
import textwrap
from typing import Optional

log = logging.getLogger(__name__)

# ── Intent detection ──────────────────────────────────────────────────────────
_SQL_PATTERNS: list[tuple[str, list[str]]] = [
    ("balance",       ["balance", "how much", "account balance", "funds", "money left", "amount in"]),
    ("transactions",  ["transaction", "recent payment", "last payment", "spent on", "debited", "credited",
                       "statement", "history", "purchase"]),
    ("emi",           ["emi", "installment", "repayment", "loan payment", "next emi", "due date"]),
    ("loans",         ["loan", "outstanding loan", "home loan status", "personal loan status"]),
    ("credit_score",  ["credit score", "cibil", "credit rating", "credit report"]),
]
_RAG_PATTERNS: list[tuple[str, list[str]]] = [
    ("faq",           ["how do i", "how to", "activate", "reset password", "upi limit", "block card",
                       "kyc", "open account", "helpline", "branch"]),
    ("rbi",           ["rbi", "repo rate", "regulation", "rbi guideline", "rbi circular",
                       "reserve bank", "compliance", "mandate", "eblr"]),
    ("loan_info",     ["loan policy", "interest rate", "eligibility", "processing fee",
                       "home loan rate", "personal loan rate", "education loan"]),
    ("insurance",     ["insurance", "policy", "premium", "coverage", "claim", "health cover",
                       "accidental", "sum assured"]),
]

# ── PII masking ───────────────────────────────────────────────────────────────
_PII_PATTERNS = [
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),   "XXXX-XXXX-XXXX"),   # Aadhaar
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),              "XXXXX9999X"),        # PAN
    (re.compile(r"\b\d{9,18}\b"),                          "ACCT-MASKED"),       # account numbers
    (re.compile(r"\b[6-9]\d{9}\b"),                        "PHONE-MASKED"),      # Indian mobile
]
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions?", re.I),
    re.compile(r"you are now", re.I),
    re.compile(r"system\s*prompt", re.I),
    re.compile(r"(drop|delete|truncate|update|insert)\s+(table|from|into)", re.I),
    re.compile(r"--\s*$", re.M),
]


def _mask_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _is_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def _classify_intent(query: str) -> tuple[str, str]:
    """Returns (route, intent) where route is 'sql' or 'rag'."""
    q = query.lower()
    for intent, kws in _SQL_PATTERNS:
        if any(kw in q for kw in kws):
            return "sql", intent
    for intent, kws in _RAG_PATTERNS:
        if any(kw in q for kw in kws):
            return "rag", intent
    return "rag", "faq"   # default to FAQ RAG


# ── SQL data fetcher ──────────────────────────────────────────────────────────
def _fetch_sql_context(intent: str, customer_id: int) -> str:
    """Fetch structured banking data from MySQL based on intent."""
    try:
        from app import db
        from app.models import Account, Transaction, Loan, EMI, CreditScore

        if intent == "balance":
            accounts = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
            lines = [f"Account ({a.account_type}): {a.account_number} — Balance: ₹{a.balance:,.2f}"
                     for a in accounts]
            return "Customer Account Balances:\n" + "\n".join(lines) if lines else "No active accounts found."

        elif intent == "transactions":
            accounts    = Account.query.filter_by(customer_id=customer_id).all()
            account_ids = [a.id for a in accounts]
            txs = Transaction.query.filter(
                Transaction.account_id.in_(account_ids)
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            lines = [
                f"{tx.timestamp.strftime('%Y-%m-%d')} | {tx.transaction_type.upper()} | "
                f"₹{tx.amount:,.2f} | {tx.merchant or tx.description or 'Transfer'} | {tx.category}"
                for tx in txs
            ]
            return "Recent 10 Transactions:\n" + "\n".join(lines) if lines else "No recent transactions."

        elif intent == "emi":
            loans = Loan.query.filter_by(customer_id=customer_id, status='active').all()
            loan_ids = [l.id for l in loans]
            emis = EMI.query.filter(
                EMI.loan_id.in_(loan_ids), EMI.status == 'pending'
            ).order_by(EMI.due_date.asc()).limit(6).all()
            lines = [
                f"EMI #{e.installment_no} | Due: {e.due_date.strftime('%Y-%m-%d')} | "
                f"₹{e.total_amount:,.2f} (Principal: ₹{e.principal:,.2f}, Interest: ₹{e.interest:,.2f})"
                for e in emis
            ]
            return "Upcoming EMIs:\n" + "\n".join(lines) if lines else "No pending EMIs."

        elif intent == "loans":
            loans = Loan.query.filter_by(customer_id=customer_id).all()
            lines = [
                f"{l.loan_type} | Amount: ₹{l.loan_amount:,.2f} | Outstanding: ₹{l.outstanding:,.2f} | "
                f"Rate: {l.interest_rate}% | Status: {l.status}"
                for l in loans
            ]
            return "Loan Portfolio:\n" + "\n".join(lines) if lines else "No loans found."

        elif intent == "credit_score":
            cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(
                CreditScore.recorded_at.desc()).first()
            if cs:
                return (f"CIBIL Credit Score: {cs.score}\nBureau: {cs.bureau}\n"
                        f"Remarks: {cs.remarks}\nLast Updated: {cs.recorded_at.strftime('%Y-%m-%d')}")
            return "Credit score not found."

        return "Data not available."

    except Exception as exc:
        log.error("SQL fetch error for intent '%s': %s", intent, exc)
        return "Unable to fetch account data at this moment."


# ── OpenAI / Gemini call ───────────────────────────────────────────────────────
def _call_llm(system_prompt: str, user_message: str,
               history: list[dict], timeout: int = 12) -> str:
    from dotenv import load_dotenv
    load_dotenv(override=True)

    api_key  = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if not api_key:
        return ("I'm unable to generate AI responses because the LLM API key is not configured. "
                "Please set LLM_API_KEY in your .env file.")

    try:
        import openai

        if provider in ("gemini", "google"):
            base_url = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
            model = os.getenv("LLM_MODEL", "gemini-3.6-flash")
            client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        else:
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            client = openai.OpenAI(api_key=api_key, timeout=timeout)

        messages = [{"role": "system", "content": system_prompt}]
        # Include last 6 turns of history (3 exchanges)
        for turn in history[-6:]:
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=600,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()

    except ImportError:
        return ("OpenAI package not installed. Run: pip install openai")
    except openai.AuthenticationError:
        return "Invalid API key. Please check LLM_API_KEY in your .env file."
    except openai.RateLimitError:
        return "LLM rate limit reached. Please try again in a moment."
    except openai.APITimeoutError:
        return "The AI response timed out (12s limit). Please try a simpler query."
    except Exception as exc:
        log.error("LLM call failed: %s", exc)
        return f"AI service temporarily unavailable. Please try again. (Error: {type(exc).__name__})"


# ── Main orchestrator ─────────────────────────────────────────────────────────
def process_query(query: str, customer_id: int,
                  history: Optional[list[dict]] = None,
                  user_id: Optional[int] = None) -> dict:
    """
    Full pipeline. Returns:
    {
        'response':   str,
        'intent':     str,
        'route':      str,       # 'sql' | 'rag'
        'citations':  list[str],
        'latency_ms': int
    }
    """
    t0      = time.monotonic()
    history = history or []

    # ── Privacy firewall ──────────────────────────────────────────────────────
    if _is_injection(query):
        return {
            "response":   "I cannot process that request — it appears to contain unsafe instructions.",
            "intent":     "blocked",
            "route":      "blocked",
            "citations":  [],
            "latency_ms": 0,
        }

    safe_query = _mask_pii(query)

    # ── Intent classification ─────────────────────────────────────────────────
    route, intent = _classify_intent(safe_query)

    citations: list[str] = []

    if route == "sql":
        # ── Route A: structured banking data ─────────────────────────────────
        context = _fetch_sql_context(intent, customer_id)
        system_prompt = textwrap.dedent(f"""
            You are SentinelBank AI Copilot, a trusted banking assistant.
            You have access to the customer's real account data below.
            Answer the customer's question accurately and concisely using the data.
            Never reveal full account numbers — use masked versions.
            Format currency in Indian Rupees (₹). Be brief and professional.

            --- CUSTOMER ACCOUNT DATA ---
            {context}
        """).strip()

    else:
        # ── Route B: RAG document retrieval ──────────────────────────────────
        from app.rag.retriever import retrieve
        rag_result = retrieve(safe_query)
        context    = rag_result["context"]
        citations  = rag_result["citations"]

        if not context:
            context = "No relevant policy documents found."

        system_prompt = textwrap.dedent(f"""
            You are SentinelBank AI Copilot, a knowledgeable banking assistant.
            Answer using the provided SentinelBank policy context.
            If the answer is not in the context, say so honestly — do not fabricate.
            Be concise, clear, and professional.

            --- POLICY CONTEXT ---
            {context}
        """).strip()

    # ── LLM call ──────────────────────────────────────────────────────────────
    response = _call_llm(system_prompt, safe_query, history)

    # ── Audit log ─────────────────────────────────────────────────────────────
    try:
        from app.models import AuditLog
        from app import db
        entry = AuditLog(
            user_id=user_id,
            action="ai_chat",
            resource=intent,
            ip_address="internal",
            details=f"route={route} len={len(response)}"
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        pass   # Audit failure must never break the chat

    latency_ms = int((time.monotonic() - t0) * 1000)
    return {
        "response":   response,
        "intent":     intent,
        "route":      route,
        "citations":  citations,
        "latency_ms": latency_ms,
    }
