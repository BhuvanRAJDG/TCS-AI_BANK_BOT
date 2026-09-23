"""
app/rag/ingest.py
Ingest text documents into ChromaDB collections.
Supports plain-text seed data so the RAG works immediately
without needing external PDFs. PDF ingestion via PyMuPDF
is also supported when files are placed in data/docs/.
"""
from __future__ import annotations
import os
import hashlib
import logging
from typing import Optional

from .chroma_client import get_collection, is_available

log = logging.getLogger(__name__)

# ── Seed FAQ / policy data ────────────────────────────────────────────────────
SEED_DOCS: dict[str, list[dict]] = {
    "faqs": [
        {"id": "faq_1", "text": "How do I reset my SentinelBank internet banking password? You can reset your password by clicking 'Forgot Password' on the login page. An OTP will be sent to your registered mobile number and email address. Enter the OTP, then set a new password. The password must be at least 8 characters and contain uppercase, lowercase, numbers, and special characters.", "source": "SentinelBank FAQ"},
        {"id": "faq_2", "text": "How do I activate my SentinelBank debit card? To activate your debit card, log in to internet banking, go to Cards section, select your card and click Activate. You can also activate through our mobile app or by visiting the nearest branch with your card and valid KYC documents.", "source": "SentinelBank FAQ"},
        {"id": "faq_3", "text": "What is the daily UPI transaction limit for SentinelBank? The default daily UPI transaction limit is ₹1,00,000 per day. You can request an increase up to ₹5,00,000 per day by submitting a request through internet banking or visiting the branch.", "source": "SentinelBank FAQ"},
        {"id": "faq_4", "text": "How do I report an unauthorized transaction on my SentinelBank account? Immediately call our 24x7 helpline 1800-XXX-XXXX or use the Fraud Center in the app. Block your card and file a dispute. Under RBI guidelines, if reported within 3 working days of the bank statement date, you are entitled to zero liability for third-party fraud.", "source": "SentinelBank FAQ"},
        {"id": "faq_5", "text": "What documents are required to open a SentinelBank savings account? You need: (1) PAN Card, (2) Aadhaar Card for address proof, (3) Recent passport-size photograph. For NRIs, additional documents like passport, visa, and foreign address proof are required.", "source": "SentinelBank FAQ"},
    ],
    "rbi_guidelines": [
        {"id": "rbi_1", "text": "RBI Repo Rate and Lending Rates: The Reserve Bank of India's repo rate determines the benchmark lending rates for all Indian banks. Banks price their loans using the External Benchmark Lending Rate (EBLR) linked to the repo rate. As of 2024, banks must reset floating-rate loans linked to external benchmarks at least once every three months.", "source": "RBI Monetary Policy 2024"},
        {"id": "rbi_2", "text": "RBI KYC Norms: All banks must conduct Customer Due Diligence (CDD) under the Prevention of Money Laundering Act. Periodic KYC update is mandatory: High-risk customers every 2 years, medium-risk every 8 years, low-risk every 10 years. Aadhaar-based eKYC is accepted for digital account opening.", "source": "RBI KYC Guidelines 2023"},
        {"id": "rbi_3", "text": "RBI guidelines on digital lending: Digital lending apps must disburse loans directly into borrower's bank accounts. EMI repayments must come from the borrower's bank account only. No middleman can handle borrower funds. All digital lenders must be registered NBFCs or banks.", "source": "RBI Digital Lending Guidelines 2022"},
        {"id": "rbi_4", "text": "RBI Circular on Unauthorized Electronic Transactions: Customers have zero liability if the fraud is due to bank negligence or a third-party breach and reported within 3 working days. Limited liability of ₹5,000-₹25,000 applies if reported between 4-7 days depending on account type. Beyond 7 days, liability is determined case-by-case.", "source": "RBI Circular RBI/2017-18/15"},
    ],
    "loan_policies": [
        {"id": "loan_1", "text": "SentinelBank Home Loan Policy: We offer home loans from ₹10 lakh to ₹5 crore at interest rates starting from 8.40% per annum (floating) linked to RBI Repo Rate. Maximum tenure is 30 years. Loan-to-Value ratio is up to 90% for loans up to ₹30 lakh, 80% for ₹30-75 lakh, and 75% above ₹75 lakh. Processing fee is 0.5% of loan amount, minimum ₹10,000.", "source": "SentinelBank Home Loan Policy"},
        {"id": "loan_2", "text": "SentinelBank Personal Loan Policy: Personal loans are available from ₹50,000 to ₹40 lakh for salaried individuals with minimum monthly income of ₹25,000. Interest rates range from 10.99% to 22% per annum. Maximum tenure is 60 months. No collateral required. Processing fee is 2-3% of loan amount. Prepayment is free after 12 EMIs.", "source": "SentinelBank Personal Loan Policy"},
        {"id": "loan_3", "text": "SentinelBank Car Loan Policy: Finance up to 100% of on-road price for new cars, 80% for used cars. Interest rates from 8.75% to 14% per annum. Tenure from 12 to 84 months. Eligible for salaried individuals earning ₹20,000 per month or self-employed with ITR of ₹2 lakh per annum. Part prepayment allowed after 6 EMIs.", "source": "SentinelBank Auto Loan Policy"},
        {"id": "loan_4", "text": "SentinelBank Education Loan Policy: Loans up to ₹10 lakh for studies in India and ₹20 lakh for abroad without collateral. Above these limits, collateral or third-party guarantee is required. Moratorium period covers course duration plus 1 year. Simple interest charged during moratorium. Tax benefit available under Section 80E on interest paid.", "source": "SentinelBank Education Loan Policy"},
    ],
    "insurance_policies": [
        {"id": "ins_1", "text": "SentinelBank Accidental Death Insurance: Coverage of ₹10 lakh automatically for all SentinelBank account holders at no extra cost. In case of accidental death, the nominee registered in the bank account receives ₹10 lakh. Claim must be filed within 90 days of the accident with death certificate, FIR copy, and post-mortem report.", "source": "SentinelBank Insurance Policy"},
        {"id": "ins_2", "text": "SentinelBank Health Insurance Tie-Up: We partner with HDFC ERGO and Star Health for group health insurance starting at ₹4,999 per year for ₹5 lakh coverage. Family floater plans cover self, spouse, and 2 dependent children. Pre-existing disease covered after 3 year waiting period. Cashless treatment at 10,000+ hospitals across India.", "source": "SentinelBank Health Insurance"},
        {"id": "ins_3", "text": "Home Loan Insurance (HLPP): Home Loan Protection Plan is recommended for all SentinelBank home loan borrowers. Single premium option available. In case of borrower's death, the outstanding loan is paid off by the insurance company, protecting the family. The premium is eligible for deduction under Section 80C.", "source": "SentinelBank HLPP Policy"},
    ],
}


def _chunk_text(text: str, max_words: int = 400) -> list[str]:
    """Split text into chunks of at most max_words words."""
    words  = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + max_words]))
        i += max_words
    return chunks


def ingest_seed_data() -> dict[str, int]:
    """Ingest all seed documents into ChromaDB. Returns counts per collection."""
    if not is_available():
        log.warning("ChromaDB not available — skipping seed ingestion")
        return {}

    counts = {}
    for col_name, docs in SEED_DOCS.items():
        col = get_collection(col_name)
        if col is None:
            continue

        ids, texts, metas = [], [], []
        for doc in docs:
            chunks = _chunk_text(doc["text"])
            for ci, chunk in enumerate(chunks):
                doc_id = f"{doc['id']}_c{ci}"
                ids.append(doc_id)
                texts.append(chunk)
                metas.append({"source": doc.get("source", col_name), "doc_id": doc["id"]})

        if ids:
            try:
                existing = col.get(ids=ids)
                existing_ids = set(existing["ids"]) if existing["ids"] else set()
                new_idx = [i for i, did in enumerate(ids) if did not in existing_ids]
                if new_idx:
                    col.add(
                        ids=[ids[i] for i in new_idx],
                        documents=[texts[i] for i in new_idx],
                        metadatas=[metas[i] for i in new_idx],
                    )
                    log.info("Ingested %d chunks into collection '%s'", len(new_idx), col_name)
                counts[col_name] = len(new_idx)
            except Exception as exc:
                log.error("Ingest error for %s: %s", col_name, exc)
    return counts


def ingest_pdf(file_path: str, collection_name: str) -> int:
    """Ingest a PDF file into a named collection. Returns number of chunks added."""
    if not is_available():
        log.warning("ChromaDB not available")
        return 0
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.warning("PyMuPDF not installed. pip install pymupdf")
        return 0

    col = get_collection(collection_name)
    if col is None:
        return 0

    doc      = fitz.open(file_path)
    full_text = " ".join(page.get_text() for page in doc)
    chunks   = _chunk_text(full_text)

    base_id = hashlib.md5(file_path.encode()).hexdigest()[:8]
    ids     = [f"{base_id}_c{i}" for i in range(len(chunks))]
    metas   = [{"source": os.path.basename(file_path), "page_approx": i} for i in range(len(chunks))]

    col.add(ids=ids, documents=chunks, metadatas=metas)
    log.info("Ingested PDF %s → %d chunks → %s", file_path, len(chunks), collection_name)
    return len(chunks)
