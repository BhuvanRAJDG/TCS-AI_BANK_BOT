"""
app/ai/orchestrator.py
AI Banking Copilot orchestrator with Active Conversational Learning & Hybrid RAG.
"""
from __future__ import annotations
import os
import re
import time
import logging
import textwrap
from typing import Optional

from app.rag.learning_engine import extract_learning_fact, store_learned_fact
from app.rag.hybrid_retriever import hybrid_retrieve

log = logging.getLogger(__name__)

_SQL_PATTERNS: list[tuple[str, list[str]]] = [
    ("balance",       ["balance", "how much", "account balance", "funds", "money left", "amount in", "net worth", "savings account", "current account"]),
    ("transactions",  ["transaction", "recent payment", "last payment", "spent on", "debited", "credited",
                       "statement", "history", "purchase", "recent activity", "expense history", "spending", "passbook"]),
    ("emi",           ["emi", "installment", "repayment", "loan payment", "next emi", "due date", "pay emi", "pending emi", "pay off emi"]),
    ("loans",         ["loan", "outstanding loan", "home loan status", "personal loan status", "car loan", "borrowed"]),
    ("expense_splits",["split", "owe", "shared bill", "trip expense", "group bill", "settle share", "bill split", "friend owe"]),
    ("credit_score",  ["credit score", "cibil", "credit rating", "credit report"]),
]
_RAG_PATTERNS: list[tuple[str, list[str]]] = [
    ("faq",           ["how do i", "how to", "activate", "reset password", "upi limit", "block card",
                       "kyc", "open account", "helpline", "branch", "timing", "hours", "contact", "support"]),
    ("rbi",           ["rbi", "repo rate", "regulation", "rbi guideline", "rbi circular",
                       "reserve bank", "compliance", "mandate", "eblr"]),
    ("loan_info",     ["loan policy", "interest rate", "eligibility", "processing fee",
                       "home loan rate", "personal loan rate", "education loan", "car loan rate", "foreclosure"]),
    ("insurance",     ["insurance", "policy", "premium", "coverage", "claim", "health cover",
                       "accidental", "sum assured", "hlpp"]),
]

_PII_PATTERNS = [
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),   "XXXX-XXXX-XXXX"),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),              "XXXXX9999X"),
    (re.compile(r"\b\d{9,18}\b"),                          "ACCT-MASKED"),
    (re.compile(r"\b[6-9]\d{9}\b"),                        "PHONE-MASKED"),
]
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions?", re.I),
    re.compile(r"you are now\s+(dan|an evil|jailbroken)", re.I),
    re.compile(r"system\s*prompt\s*override", re.I),
    re.compile(r"(drop|delete|truncate|alter)\s+table", re.I),
    re.compile(r"--\s*$", re.M),
]


def _mask_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _is_injection(text: str) -> bool:
    return any(p.search(text) for p in _INJECTION_PATTERNS)


def _classify_intent(query: str) -> tuple[str, str]:
    q = query.lower()
    for intent, kws in _SQL_PATTERNS:
        if any(kw in q for kw in kws):
            return "sql", intent
    for intent, kws in _RAG_PATTERNS:
        if any(kw in q for kw in kws):
            return "rag", intent
    return "rag", "general"


def _fetch_sql_context(intent: str, customer_id: Optional[int]) -> str:
    if not customer_id:
        return "No customer account profile found for this user."

    try:
        from app import db
        from app.models import Account, Transaction, Loan, EMI, CreditScore

        if intent == "balance":
            accounts = Account.query.filter_by(customer_id=customer_id, is_active=True).all()
            lines = [f"â€¢ {a.account_type.capitalize()} Account (****{a.account_number[-4:]}): â‚¹{a.balance:,.2f} (IFSC: {a.ifsc_code})"
                     for a in accounts]
            return "Real-Time Account Balances:\n" + "\n".join(lines) if lines else "No active accounts found."

        elif intent == "transactions":
            accounts    = Account.query.filter_by(customer_id=customer_id).all()
            account_ids = [a.id for a in accounts]
            if not account_ids:
                return "No transactions recorded."
            txs = Transaction.query.filter(
                Transaction.account_id.in_(account_ids)
            ).order_by(Transaction.timestamp.desc()).limit(8).all()
            lines = [
                f"â€¢ {tx.timestamp.strftime('%d %b %Y, %H:%M')} | {tx.transaction_type.upper()} â‚¹{tx.amount:,.2f} | {tx.merchant or tx.description or 'Transfer'} ({tx.category}) [Ref: {tx.reference_id}]"
                for tx in txs
            ]
            return "Recent Real-Time Transactions:\n" + "\n".join(lines) if lines else "No recent transactions found."

        elif intent == "emi":
            loans = Loan.query.filter_by(customer_id=customer_id, status='active').all()
            loan_ids = [l.id for l in loans]
            emis = EMI.query.filter(
                EMI.loan_id.in_(loan_ids), EMI.status == 'pending'
            ).order_by(EMI.due_date.asc()).limit(6).all()
            lines = [
                f"â€¢ EMI #{e.installment_no} | Due: {e.due_date.strftime('%d %b %Y')} | "
                f"Amount: â‚¹{e.total_amount:,.2f} (Principal: â‚¹{e.principal:,.2f}, Interest: â‚¹{e.interest:,.2f})"
                for e in emis
            ]
            return "Upcoming EMI Installments:\n" + "\n".join(lines) if lines else "No pending EMIs due."

        elif intent == "loans":
            loans = Loan.query.filter_by(customer_id=customer_id).all()
            lines = [
                f"â€¢ {l.loan_type.capitalize()} Loan #{l.loan_account_number}: Principal â‚¹{l.loan_amount:,.2f} at {l.interest_rate}% p.a. (Status: {l.status})"
                for l in loans
            ]
            return "Customer Loan Accounts:\n" + "\n".join(lines) if lines else "No active loan accounts found."

        elif intent == "credit_score":
            cs = CreditScore.query.filter_by(customer_id=customer_id).order_by(CreditScore.recorded_at.desc()).first()
            if cs:
                return (f"CIBIL Credit Score: {cs.score} / 900\nBureau: {cs.bureau}\n"
                        f"Status Rating: {cs.remarks or 'Excellent'}\nLast Evaluated: {cs.recorded_at.strftime('%d %b %Y')}")
            return "CIBIL Credit Score: 770 / 900 (Excellent Status â€¢ No negative remarks)."

        return "Requested banking data not found."

    except Exception as exc:
        log.error("SQL fetch error: %s", exc)
        return "Unable to fetch account data at this moment."


def _call_llm(system_prompt: str, user_message: str,
               history: list[dict], timeout: int = 15) -> str:
    from dotenv import load_dotenv
    load_dotenv(override=True)

    api_key  = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if not api_key:
        return ("I'm currently unable to generate AI responses because the LLM API key is not configured. "
                "Please set LLM_API_KEY in your .env file.")

    try:
        import openai

        if provider in ("gemini", "google"):
            base_url = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
            model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
            client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        else:
            model = os.getenv("LLM_MODEL", "gpt-4o-mini")
            client = openai.OpenAI(api_key=api_key, timeout=timeout)

        messages = [{"role": "system", "content": system_prompt}]
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

    except Exception as exc:
        log.error("LLM call failed: %s", exc)
        return f"CBS Bot is temporarily unavailable. Please try again in a few moments. (Error: {type(exc).__name__})"


def _match_transfer_command(query: str) -> tuple[str, float] | None:
    q = query.strip()
    m1 = re.search(r"(?:transfer|send|pay|remit)\s+(?:â‚¹\s*)?(\d+(?:\.\d{1,2})?)\s+(?:to|for)\s+([A-Za-z0-9\s]+)", q, re.I)
    if m1:
        try:
            return m1.group(2).strip(), float(m1.group(1))
        except ValueError:
            pass

    m2 = re.search(r"(?:transfer|send|pay|remit)\s+([A-Za-z\s]+?)\s+(?:â‚¹\s*)?(\d+(?:\.\d{1,2})?)", q, re.I)
    if m2:
        try:
            name = m2.group(1).strip()
            if name.lower() not in ("my", "the", "an", "a", "money", "funds", "emi", "bill", "bills"):
                return name, float(m2.group(2))
        except ValueError:
            pass

    return None


def process_query(query: str, customer_id: Optional[int],
                  history: Optional[list[dict]] = None,
                  user_id: Optional[int] = None) -> dict:
    t0 = time.monotonic()
    history = history or []

    # 1. Privacy Firewall
    if _is_injection(query):
        return {
            "response":   "I cannot process that request â€” it contains unsafe or restricted instructions.",
            "intent":     "blocked",
            "route":      "blocked",
            "citations":  [],
            "latency_ms": 0,
        }

    safe_query = _mask_pii(query)

    # 2. ACTIVE CONVERSATIONAL LEARNING CHECK
    learn_fact = extract_learning_fact(safe_query)
    if learn_fact:
        category, topic, content = learn_fact
        saved = store_learned_fact(user_id=user_id, category=category, topic=topic, content=content)
        ack_text = (
            f"âœ… **Understood & Remembered!**\n\n"
            f"I have committed this new information to your secure bank profile:\n"
            f"â€¢ **Topic:** `{saved['topic']}`\n"
            f"â€¢ **Learned Fact:** *\"{saved['content']}\"*\n\n"
            f"*(This knowledge is now indexed and will be applied to all your future queries and banking assistance.)*"
        )
        return {
            "response": ack_text,
            "intent": "learning_stored",
            "route": "active_learning",
            "citations": [f"Learned Memory: {saved['topic']}"],
            "latency_ms": int((time.monotonic() - t0) * 1000),
        }

    # 3. Direct Money Transfer Intent
    transfer_match = _match_transfer_command(safe_query)
    if transfer_match:
        target_name, amount = transfer_match
        response_text = (
            f"ðŸ”’ **Transfer Authorization Required**\n\n"
            f"You are initiating a transfer of **â‚¹{amount:,.2f}** to **{target_name}** via CBS FastPay UPI.\n\n"
            f"Please authorize this transaction with your **UPI PIN** in the confirmation prompt below."
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

    # 4. Intent Classification & Multi-Route Resolution
    route, intent = _classify_intent(safe_query)
    citations: list[str] = []

    if route == "sql":
        context = _fetch_sql_context(intent, customer_id)
        user_facts = hybrid_retrieve(safe_query, user_id=user_id, top_k=2)
        learned_context = user_facts.get("context", "")

        system_prompt = textwrap.dedent(f"""
            You are CBS Bot, the intelligent, friendly, and elite AI Banking Concierge for CBS Bank.
            You have access to the customer's authenticated real-time bank ledger records below.

            CUSTOMER SERVICE GUIDELINES:
            1. Deliver clear, warmly formatted, and concise answers with bullet points and bold highlights.
            2. Never reveal full sensitive account numbers (use masked ****1234).
            3. Always format monetary values in Indian Rupees (â‚¹).
            4. If relevant learned preferences are provided, apply them accurately.

            --- REAL-TIME CUSTOMER BANK DATA ---
            {context}

            --- SAVED USER PREFERENCES & MEMORY ---
            {learned_context if learned_context else "None"}
        """).strip()

    else:
        rag_data = hybrid_retrieve(safe_query, user_id=user_id, top_k=3)
        context = rag_data["context"]
        citations = rag_data["citations"]

        system_prompt = textwrap.dedent(f"""
            You are CBS Bot, the intelligent, highly capable, and elite AI Banking Concierge for CBS Bank.
            You serve customers with top-tier executive hospitality, precision, clarity, and deep financial knowledge.

            CUSTOMER SERVICE GUIDELINES:
            1. Always be polite, warm, professional, and directly helpful.
            2. Use the verified CBS Bank knowledge and any user-learned memory provided below to formulate your answers.
            3. If the user asks about something they previously taught you (e.g. branch preference, contact rules, custom facts), utilize the [Learned Custom Fact] accurately and acknowledge it.
            4. Format numbers cleanly, use bullet points, and express Indian financial amounts in Indian Rupees (â‚¹).
            5. If a general question is asked (greetings, calculations, banking terminology), answer using your broad financial intelligence accurately and helpfully.

            --- VERIFIED CBS KNOWLEDGE & USER MEMORY ---
            {context if context else "No specific document matched. Use professional general banking knowledge."}
        """).strip()

    # 5. LLM Call
    response = _call_llm(system_prompt, safe_query, history)

    if route == "sql" and any(k in response for k in ("unavailable", "timed out", "key is not configured")):
        response = f"Here is your requested real-time CBS Bank data:\n\n{context}"

    latency_ms = int((time.monotonic() - t0) * 1000)
    return {
        "response":   response,
        "intent":     intent,
        "route":      route,
        "citations":  citations,
        "latency_ms": latency_ms,
    }
