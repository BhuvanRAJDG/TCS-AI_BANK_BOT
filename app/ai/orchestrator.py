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
    ("balance",       ["balance", "how much", "account balance", "funds", "money left", "amount in", "net worth", "savings account", "current account"]),
    ("transactions",  ["transaction", "recent payment", "last payment", "spent on", "debited", "credited",
                       "statement", "history", "purchase", "recent activity", "expense history", "spending"]),
    ("emi",           ["emi", "installment", "repayment", "loan payment", "next emi", "due date", "pay emi", "pending emi", "pay off emi"]),
    ("loans",         ["loan", "outstanding loan", "home loan status", "personal loan status", "car loan", "borrowed"]),
    ("expense_splits",["split", "owe", "shared bill", "trip expense", "group bill", "settle share", "bill split", "friend owe"]),
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
    """Fetch structured banking data from database based on intent."""
    try:
        from app import db
        from app.models import Account, Transaction, Loan, EMI, CreditScore
        from app.models.expense_split import ExpenseSplit, ExpenseSplitParticipant

        if intent == "balance":
            accounts = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
            lines = [f"• {a.account_type.capitalize()} Account ({a.account_number[-4:]}): ₹{a.balance:,.2f} (IFSC: {a.ifsc_code})"
                     for a in accounts]
            return "Customer Account Balances:\n" + "\n".join(lines) if lines else "No active accounts found."

        elif intent == "transactions":
            accounts    = Account.query.filter_by(customer_id=customer_id).all()
            account_ids = [a.id for a in accounts]
            txs = Transaction.query.filter(
                Transaction.account_id.in_(account_ids)
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            lines = [
                f"• {tx.timestamp.strftime('%d %b %Y')} | {tx.transaction_type.upper()} ₹{tx.amount:,.2f} | {tx.merchant or tx.description or 'Transfer'} ({tx.category})"
                for tx in txs
            ]
            return "Recent 10 Transactions (Real-Time Data):\n" + "\n".join(lines) if lines else "No recent transactions found."

        elif intent == "emi":
            loans = Loan.query.filter_by(customer_id=customer_id, status='active').all()
            loan_ids = [l.id for l in loans]
            emis = EMI.query.filter(
                EMI.loan_id.in_(loan_ids), EMI.status == 'pending'
            ).order_by(EMI.due_date.asc()).limit(6).all()
            lines = [
                f"• EMI #{e.installment_no} | Due: {e.due_date.strftime('%d %b %Y')} | "
                f"Amount: ₹{e.total_amount:,.2f} (Principal: ₹{e.principal:,.2f}, Interest: ₹{e.interest:,.2f})"
                for e in emis
            ]
            prompt_note = "\n\n(Note for CBS Bot: Proactively ask the user if they would like to pay off their upcoming EMI right now by visiting the Loans section!)."
            return ("Upcoming Pending EMIs:\n" + "\n".join(lines) + prompt_note) if lines else "You currently have no pending EMI installments."

        elif intent == "expense_splits":
            user_participations = ExpenseSplitParticipant.query.filter_by(customer_id=customer_id).all()
            split_ids = {p.split_id for p in user_participations}
            user_splits = ExpenseSplit.query.filter(ExpenseSplit.id.in_(split_ids)).order_by(ExpenseSplit.created_at.desc()).all()
            
            lines = []
            for s in user_splits:
                user_p = next((p for p in s.participants if p.customer_id == customer_id), None)
                status_str = "Paid ✓" if (user_p and user_p.paid) else f"Unpaid Share: ₹{user_p.share_amount:,.2f}" if user_p else ""
                lines.append(f"• Group: '{s.title}' | Total Spend: ₹{s.total_amount:,.2f} | Your Status: {status_str}")

            prompt_note = "\n\n(Note for CBS Bot: Proactively ask the user if they would like to settle up their pending bill splits now on the Split Expenses page!)."
            return ("Active Group Expense Splits:\n" + "\n".join(lines) + prompt_note) if lines else "No active group expense splits found."

        elif intent == "loans":
            loans = Loan.query.filter_by(customer_id=customer_id).all()
            lines = [
                f"• {l.loan_type} | Sanctioned Amount: ₹{l.loan_amount:,.2f} | Outstanding Balance: ₹{l.outstanding:,.2f} | "
                f"Interest Rate: {l.interest_rate}% | Status: {l.status.upper()}"
                for l in loans
            ]
            return "Loan Portfolio Details:\n" + "\n".join(lines) if lines else "No loans found in your profile."

        elif intent == "credit_score":
            cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(
                CreditScore.recorded_at.desc()).first()
            if cs:
                return (f"CIBIL Credit Score: {cs.score} / 900\nBureau: {cs.bureau}\n"
                        f"Status Rating: {cs.remarks}\nLast Evaluated: {cs.recorded_at.strftime('%d %b %Y')}")
            return "Credit score details currently unavailable."

        return "Requested data not found."

    except Exception as exc:
        log.error("SQL fetch error for intent '%s': %s", intent, exc)
        return "Unable to fetch account data at this moment."


# ── OpenAI / Gemini call with Retry Backoff ──────────────────────────────────
def _call_llm(system_prompt: str, user_message: str,
               history: list[dict], timeout: int = 15) -> str:
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

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=600,
                    temperature=0.3,
                )
                return resp.choices[0].message.content.strip()
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    time.sleep(2.5 * (attempt + 1))
                else:
                    raise

    except ImportError:
        return ("OpenAI package not installed. Run: pip install openai")
    except openai.AuthenticationError:
        return "Invalid API key. Please check LLM_API_KEY in your .env file."
    except openai.RateLimitError:
        return "CSB Bot is currently experiencing high demand. Please try sending your query again in a few seconds."
    except openai.APITimeoutError:
        return "The AI response timed out (15s limit). Please try a simpler query."
    except Exception as exc:
        log.error("LLM call failed: %s", exc)
        return f"CSB Bot is temporarily unavailable. Please try again. (Error: {type(exc).__name__})"


def _match_transfer_command(query: str) -> tuple[str, float] | None:
    """Regex pattern matcher to extract (recipient_name, amount) from natural language query."""
    q = query.strip()
    # Pattern 1: "transfer 500 to Priya", "pay 1200 to Rohit", "send 350 to Aarav"
    m1 = re.search(r"(?:transfer|send|pay|remit)\s+(?:₹\s*)?(\d+(?:\.\d{1,2})?)\s+(?:to|for)\s+([A-Za-z0-9\s]+)", q, re.I)
    if m1:
        try:
            return m1.group(2).strip(), float(m1.group(1))
        except ValueError:
            pass

    # Pattern 2: "pay Priya 500", "send Aarav 1000"
    m2 = re.search(r"(?:transfer|send|pay|remit)\s+([A-Za-z\s]+?)\s+(?:₹\s*)?(\d+(?:\.\d{1,2})?)", q, re.I)
    if m2:
        try:
            name = m2.group(1).strip()
            if name.lower() not in ("my", "the", "an", "a", "money", "funds", "emi", "bill", "bills"):
                return name, float(m2.group(2))
        except ValueError:
            pass

    return None


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

    # ── Check for direct transfer / payment command ────────────────────────────
    transfer_match = _match_transfer_command(safe_query)
    if transfer_match:
        target_name, amount = transfer_match
        response_text = (
            f"🔒 **Transfer Authorization Required**\n\n"
            f"You are initiating a transfer of **₹{amount:,.2f}** to **{target_name}** via CBS FastPay UPI.\n\n"
            f"Please authorize this transaction with your **UPI PIN** (Demo: `1234`) or account password in the confirmation prompt below."
        )
        return {
            "response": response_text,
            "intent": "transfer_pending",
            "route": "sql",
            "citations": [],
            "transfer_data": {
                "recipient": target_name,
                "amount": amount
            },
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }

    # ── Intent classification ─────────────────────────────────────────────────
    route, intent = _classify_intent(safe_query)

    citations: list[str] = []

    if route == "sql":
        # ── Route A: structured banking data ─────────────────────────────────
        context = _fetch_sql_context(intent, customer_id)
        system_prompt = textwrap.dedent(f"""
            You are CBS Bot, the intelligent, friendly, and secure AI Banking Assistant for CBS Bank.
            You have access to the customer's real account data below.
            Answer the customer's question accurately, warmly, and concisely using the data.
            Never reveal full account numbers — use masked versions.
            Format currency in Indian Rupees (₹). Be clear, concise, and professional.

            --- CUSTOMER ACCOUNT DATA ---
            {context}
        """).strip()

    else:
        # ── Route B: RAG document retrieval + General AI Conversational Intelligence ──────────────────
        from app.rag.retriever import retrieve
        rag_result = retrieve(safe_query)
        context    = rag_result["context"]
        citations  = rag_result["citations"]

        system_prompt = textwrap.dedent(f"""
            You are CBS Bot, the intelligent, friendly, and highly capable AI Banking Assistant for CBS Bank.
            You help customers with banking questions, financial calculations, policy explanations, account guidance, and general conversation.

            GUIDELINES:
            1. Always identify as CBS Bot when asked about your identity.
            2. Be warm, professional, helpful, and highly responsive to ANY user query or greeting.
            3. Use the provided CBS Bank policy context below if relevant. If the context does not contain the answer or if the user is asking a general question (such as greetings, financial advice, math, or banking terminology), answer using your broad financial knowledge politely and accurately.
            4. Format numbers cleanly and use Indian Rupees (₹) when referencing Indian financial figures.

            --- POLICY / KNOWLEDGE CONTEXT ---
            {context if context else "No specific document matched."}
        """).strip()

    # ── LLM call ──────────────────────────────────────────────────────────────
    response = _call_llm(system_prompt, safe_query, history)

    # Guaranteed fallback to direct structured data if LLM is rate-limited on SQL queries
    if route == "sql" and any(k in response for k in ("high demand", "unavailable", "rate limit", "timed out")):
        response = f"Here is your requested real-time CBS Bank data:\n\n{context}"

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
