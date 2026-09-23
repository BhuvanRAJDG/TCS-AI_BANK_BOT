# SentinelBank AI 🏦

### Enterprise-Grade Multilingual AI Banking Copilot

SentinelBank AI is a production-inspired banking platform that combines secure digital banking with Generative AI. It delivers multilingual banking assistance, Retrieval-Augmented Generation (RAG), fraud intelligence, JWT-based authentication, and a premium fintech dashboard built using Flask, MySQL, ChromaDB, and GPT-4o.

> **Designed for TCS Technology Day • AI + Banking + Cybersecurity**

---

## 🚀 Features

### Digital Banking

* Secure customer login & registration
* JWT authentication with refresh tokens
* Multi-factor authentication (OTP)
* Role-Based Access Control (Customer / Agent / Admin)
* Customer profiles & account management
* Transaction history
* Loan & EMI tracker
* Credit score dashboard
* Insurance management
* Expense splitting
* Autopay management
* Notifications & alerts

### AI Banking Copilot

* GPT-4o powered conversational assistant
* Retrieval-Augmented Generation (RAG)
* ChromaDB vector database
* RBI guideline retrieval
* Loan & insurance policy assistant
* Context-aware banking conversations
* Source citations
* Privacy-aware responses

### Security

* bcrypt password hashing
* JWT + secure cookies
* OTP verification
* Audit logging
* Rate limiting
* Device session management
* Fraud risk detection
* PII masking
* Prompt injection protection

### UI

* Premium glassmorphism design
* Tailwind CSS
* Chart.js analytics
* Dark / Light mode
* Responsive desktop & mobile
* English, Kannada & Hindi support

---

## 🏗️ System Architecture

```text
User
│
▼
Jinja2 + Tailwind UI
│
▼
Flask Backend
┌─────────┼─────────┐
│         │         │
▼         ▼         ▼
JWT Auth   MySQL   ChromaDB
│         │         │
└─────────┼─────────┘
▼
AI Orchestrator
▼
OpenAI GPT-4o
▼
Secure Banking Response
```

---

## 🛠 Tech Stack

| Layer            | Technology                    |
| ---------------- | ----------------------------- |
| Frontend         | Flask + Jinja2 + Tailwind CSS |
| Backend          | Flask                         |
| Database         | MySQL 8                       |
| Vector DB        | ChromaDB                      |
| ORM              | SQLAlchemy                    |
| Authentication   | JWT + bcrypt + OTP            |
| AI               | OpenAI GPT-4o                 |
| Embeddings       | all-MiniLM-L6-v2              |
| Charts           | Chart.js 4.4.1                |
| Containerization | Docker                        |

---

## 📂 Project Structure

```
sentinelbank-ai/
│
├── app/
│   ├── auth/
│   ├── models/
│   ├── routes/
│   ├── controllers/
│   ├── services/
│   ├── security/
│   ├── ai/
│   ├── rag/
│   ├── templates/
│   └── static/
│
├── database/
├── seed/
├── tests/
├── docker/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔐 Authentication Workflow

1. User registers
2. Password hashed using bcrypt
3. OTP generated
4. OTP verification
5. JWT Access Token issued
6. Refresh Token stored securely
7. RBAC authorizes protected routes

---

## 🤖 AI Workflow

```
User Query
│
Language Detection
│
Intent Classification
│
Entity Extraction
│
Privacy Firewall
│
SQL / Chroma Routing
│
Prompt Builder
│
GPT-4o
│
Validated Response
```

---

## 🗃 Database Modules

* Users
* Customers
* Accounts
* Transactions
* Loans
* EMI
* Credit Scores
* Insurance
* Expense Split
* Autopay
* Notifications
* Fraud Logs
* Audit Logs
* Sessions

---

## 🧠 RAG Collections

ChromaDB stores:

* Banking FAQs
* RBI Guidelines
* Loan Policies
* Insurance Policies
* Support Documents

Documents are chunked, embedded, and retrieved using semantic similarity before GPT-4o generates grounded responses.

---

## ⚡ Quick Start

### 1. Clone

```bash
git clone https://github.com/yourusername/sentinelbank-ai.git
cd sentinelbank-ai
```

### 2. Environment

```bash
cp .env.example .env
```

Fill:

```env
LLM_PROVIDER=openai
LLM_API_KEY=YOUR_OPENAI_KEY

SECRET_KEY=...
JWT_SECRET_KEY=...
```

### 3. Run

```bash
docker compose up --build
```

### 4. Seed Database

```bash
docker compose run --rm web python -m seed.seed_database
```

Open:

**http://localhost:5000**

---

## 📊 Core Modules

| Module       | Description              |
| ------------ | ------------------------ |
| Dashboard    | Banking analytics        |
| Transactions | History & filtering      |
| Loans        | EMI & repayment          |
| Insurance    | Policy overview          |
| Fraud Center | Risk monitoring          |
| AI Chat      | GPT-4o banking assistant |
| Profile      | Customer management      |

---

## 🛡 Security Features

* JWT Authentication
* Refresh Tokens
* bcrypt Hashing
* OTP MFA
* RBAC Authorization
* Rate Limiting
* Audit Logs
* Fraud Detection
* PII Masking
* Prompt Injection Firewall

---

## 📈 Performance Targets

| Component        | Target  |
| ---------------- | ------- |
| Dashboard        | <300 ms |
| SQL Query        | <300 ms |
| Vector Retrieval | <1.5 s  |
| AI Response      | <10 s   |

---

## 👨‍💻 Authors

Developed as an enterprise AI banking solution for **TCS Technology Day**.

Built with ❤️ using Flask, MySQL, ChromaDB & GPT-4o.
-Bhuvan Raj D G
