# SentinelBank AI - Implementation Plan

## Goal Description

Build a production‑grade, enterprise‑level banking copilot named **SentinelBank AI** using the exact technology stack specified. The system will provide secure multilingual banking services, AI‑driven insights via a RAG pipeline, robust authentication (JWT + OTP + MFA), role‑based access control, fraud detection, and a premium fintech UI built with Flask, Jinja2, Tailwind CSS, and Chart.js. All components—including database schemas, vector store, AI orchestrator, Docker support, and comprehensive documentation—must be generated with no placeholder `TODO`s.

---

## User Review Required

> [!IMPORTANT]
> The following decisions require your confirmation before we proceed:
> 
> - **LLM Provider & Embedding Model**: Which large language model provider (e.g., OpenAI, Anthropic, locally hosted) and which `sentence‑transformers` model should be used for embeddings?
> - **Translation Provider**: Preferred translation service (e.g., Google Translate API, DeepL, or a mock provider).
> - **OTP Mock Service**: Do you want a simple console‑log mock or a more realistic SMTP/SMS simulation? Provide any credentials or endpoints if needed.
> - **Admin Bootstrap**: Initial admin credentials (email/password) for seeding the database.
> - **JWT Secret & Token Expiry**: Desired secret key (or we can generate a random one) and default expiration times for access and refresh tokens.
> - **Docker Base Images**: Use `python:3.11-slim` for the backend and `node` for Tailwind compile, or another base image?
> - **Chart.js Version**: Any specific version preference?
> - **Tailwind Configuration**: Custom color palette or just the default Tailwind UI?
> - **Deployment Domain / Hostnames**: Any domain names to embed in documentation/configs?
> - **Email/SMS Service Credentials**: If you prefer a real service for OTP, provide API keys; otherwise we will use a console mock.

---

## Open Questions

> [!WARNING]
> - **Multilingual Support Scope**: Should the UI be fully translated (labels, tooltips) or just the AI chat responses?
> - **Performance Targets**: The request cut off at "Average response". Please specify the target latency (e.g., < 2 s for chat, < 500 ms for dashboard widgets).
> - **Data Privacy Compliance**: Any specific compliance standards (e.g., GDPR, RBI) needed for data masking and audit logging?
> - **Fraud Engine Details**: Do you have a preferred algorithmic approach (rule‑based, ML model) or should we implement a simple risk scoring based on heuristics?
> - **Testing Strategy**: Desired coverage level and whether you want integration tests with a local MySQL container.
> - **Continuous Integration**: Should we include a GitHub Actions workflow?

---

## Proposed Changes

### Project Scaffold
- **[NEW] sentinelbank-ai/** – root project directory.
- **[NEW] app/** – Flask application package.
- **[NEW] app/auth/** – authentication blueprints, JWT utilities, OTP service.
- **[NEW] app/routes/** – route definitions for all UI pages.
- **[NEW] app/controllers/** – controller logic separating request handling from routes.
- **[NEW] app/services/** – business‑logic services (e.g., account service, fraud engine).
- **[NEW] app/models/** – SQLAlchemy ORM models covering all relational tables.
- **[NEW] app/middleware/** – RBAC, request logging, privacy firewall.
- **[NEW] app/rag/** – RAG pipeline orchestration.
- **[NEW] app/vector/** – ChromaDB vector store wrappers.
- **[NEW] app/security/** – password hashing, JWT token generation, secure cookies.
- **[NEW] app/utils/** – helpers (e.g., language detection, translation abstraction).
- **[NEW] app/templates/** – Jinja2 HTML templates for all pages.
- **[NEW] app/static/** – static assets (JS, CSS, images).
- **[NEW] app/static/tailwind/** – Tailwind source files and config.
- **[NEW] app/uploads/** – user‑uploaded files (e.g., profile images, documents).
- **[NEW] docs/** – project documentation, API specs, architecture diagrams.
- **[NEW] database/** – MySQL migration scripts (via Flask‑Migrate) and seed data.
- **[NEW] tests/** – unit and integration tests (pytest).
- **[NEW] docker/** – Dockerfile and docker‑compose configuration.
- **[NEW] requirements.txt** – pinned Python dependencies.
- **[NEW] README.md** – overview, setup, and usage instructions.
- **[NEW] .env.example** – template for environment variables.
- **[NEW] docker-compose.yml** – services: Flask app, MySQL, ChromaDB.

### Authentication & Security
- JWT generation with configurable secret and expiry.
- Refresh token rotation and storage in `sessions` table.
- bcrypt password hashing with salting.
- OTP generation (6‑digit) stored temporarily with TTL.
- Mock email/SMS sender that logs OTP to console (configurable to real provider).
- RBAC middleware enforcing `Customer`, `BankAgent`, `Admin` roles.
- Session revocation endpoint and inactivity auto‑logout.
- Remember‑device token stored as secure HttpOnly cookie.

### Database Schema (MySQL 8)
- **users** – common auth fields, role, MFA status.
- **customers** – extended profile fields (masked Aadhaar/PAN, net worth, risk profile, image path).
- **accounts**, **transactions**, **loans**, **emi**, **credit_scores**, **insurance**, **expense_splits**, **autopay**, **notifications**, **fraud_logs**, **audit_logs**, **sessions** – full PK/FK relationships, indexes for performance, constraints for data integrity.
- Seed script generating 25 realistic customer records (using Faker).

### Vector Store (ChromaDB)
- Collections: `faqs`, `rbi_guidelines`, `loan_policies`, `insurance_policies`, `support_documents`.
- PDF ingestion pipeline using PyMuPDF → chunk → embed via `sentence‑transformers` → store with metadata.
- Permission filtering based on user role and language.

### AI Orchestrator (RAG)
- Language detection (`langdetect`).
- Intent classification model (fine‑tuned or rule‑based) supporting listed intents.
- Entity extraction (spaCy or custom regex). 
- Privacy firewall that masks PII before any LLM interaction and blocks unsafe prompts.
- Authorization check against user role and intent.
- Routing: SQL queries for transactional intents, vector search for document‑based intents.
- Prompt builder with system instructions and user context.
- LLM provider abstraction layer (plug‑and‑play for OpenAI, Anthropic, etc.).
- Response validation (JSON schema, length limits) and audit logging.

### Fraud Intelligence Engine
- Heuristic risk scoring (amount thresholds, merchant risk, time anomalies, geolocation mismatch).
- Explainable output with risk level, detailed explanation, and suggested action.
- Visualization via Chart.js (risk gauge, bar charts).

### Multilingual Support
- Automatic detection via `langdetect` on each request.
- Translation layer abstracts providers; default will be a mock that returns the same text unless a real API key is supplied.
- UI template strings stored per language (JSON files) and loaded at runtime.
- Manual language switch stored in user session.

### Frontend UI
- TailwindCSS compiled via `postcss` (npm scripts) for dark/light mode.
- Responsive dashboard with widgets using Chart.js.
- AI chat widget with streaming responses.
- Accessibility and modern design (gradient backgrounds, glassmorphism effects).

### Docker & DevOps
- Multi‑stage Dockerfile: build stage for Tailwind CSS, final stage runs Flask with `gunicorn`.
- `docker-compose.yml` defines services: `web`, `db` (MySQL 8), `chroma`.
- `.env.example` lists all required environment variables (DB credentials, JWT secret, LLM API keys, etc.).
- Optional health‑check endpoint.

### Testing & CI
- Pytest suite covering auth flows, RBAC, RAG pipeline, fraud engine.
- Integration tests using a temporary MySQL container.
- GitHub Actions workflow (if requested) to run tests and build Docker image.

---

## Verification Plan

### Automated Tests
- Run `pytest` – expect >80 % coverage.
- Execute migration scripts and assert all tables are created.
- Seed database and verify 25 customers exist.
- Test JWT issuance, refresh flow, and revocation.
- Simulate OTP flow and validate MFA.
- Unit test RAG intent routing and privacy firewall blocking.
- Verify ChromaDB ingestion and similarity search returns expected documents.

### Manual Verification
- Start the Docker stack (`docker compose up --build`).
- Access the web UI, register a new customer, and go through full login + OTP flow.
- Switch languages and ensure UI updates.
- Use AI chat to ask a banking‑related question; verify no PII is leaked.
- Trigger fraud detection by creating a suspicious transaction and confirm risk score is displayed.
- Validate dark & light mode toggle and responsiveness on mobile viewport.

---

**Please review the above plan and provide answers to the open questions and any preferences. Once approved, we will proceed with generating the full codebase.**
