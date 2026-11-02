# Projeto 23 — Empório da Música — Mel

A Python customer-support agent for the Artefact AI Engineer technical challenge. Mel answers in Brazilian Portuguese using relational business data and retrieved store policies. The same tool-calling engine powers a local Streamlit chat, CLI and an official Meta WhatsApp Cloud API webhook/worker adapter.

**Status:** runnable technical prototype. Deterministic integration is tested with mocks. Real LLM, real WhatsApp and Docker execution require operator configuration and are not claimed as validated here.

## Quick start

Python **3.10** is the target runtime. From this directory:

```powershell
py -3.10 -m venv .venv23
.\.venv23\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

On Linux/macOS, create with `python3.10 -m venv .venv23` and activate with `source .venv23/bin/activate` before the same pip command.

Copy `.env.example` to `.env` (Windows: `Copy-Item .env.example .env`; Linux/macOS: `cp .env.example .env`). Set `OPENAI_API_KEY` and `OPENAI_MODEL` to a tool-capable model available in your account. A model identifier is deliberately not invented or fixed to an unverified account entitlement. Optional `OPENAI_BASE_URL` selects an OpenAI-compatible provider; compatibility must be tested separately.

```bash
python -m src.data.importer
streamlit run app.py
```

Open http://localhost:8523. Without credentials, the interface still starts and explains what configuration is missing. It does not replace the LLM with canned answers.

CLI:

```bash
python -m src.cli
python -m src.cli --demo-customer 3
```

The customer selector is a **local test identity**, not authentication. Keep Streamlit local. Client 3 owns order 1; client 18 owns multi-item order 15.

## Architecture and decisions

1. An LLM selects typed function tools; Python validates arguments and executes parameterized queries. No arbitrary model-written SQL.
2. Structured facts remain in SQLite. `products → categories`, `promotions → products`, `orders → customers`, and `order_items → orders/products` are joined explicitly.
3. A derived SQL catalog view is recalculated on reads. Editing a source workbook requires reimport; editing SQLite is reflected immediately. The workbook's copied catalog never overrides operational tables.
4. Policy retrieval is local, accent-insensitive lexical retrieval with domain aliases, section headings and PDF page references. A small eight-page manual does not require a hosted vector database. This is retrieval-augmented generation; it uses no embeddings. Misspellings and complex paraphrases remain a limitation.
5. Money uses integer cents and Decimal; installment remainders are distributed so the sum exactly matches the total. The LLM does not own arithmetic.
6. SQLite stores session history and the inbound queue. Meta acknowledgement is independent of LLM latency. A single worker is the supported deployment baseline.

The official OpenAI SDK Chat Completions tool interface was chosen for a compact, inspectable loop and optional compatible endpoints. There are at most eight tool executions per turn; external timeouts and provider retries are bounded. Conversational compliance is partly prompt-based and must be measured with real model evaluation before deployment.

## Data ingestion

`data/source/base_organizada.xlsx` contains 10 tabs. All are retained in `source_aux`; six business tables are normalized. Expected source counts: 65 products, 9 categories, 50 customers, 20 orders, 22 order items and 25 promotions, of which 4 are active.

The importer validates required fields, JSON specs, foreign keys and constraints, then UPSERTs data in a transaction. Repeating the import does not duplicate records or erase conversations. Removal of source records is deliberately **not** a destructive sync: removed rows remain until an explicit migration. Reimport overwrites operational edits for matching source IDs; back up the DB first. Source files are not modified.

`created_at` is product registration, not stock freshness. The database is a challenge snapshot, not a live ERP connection. Historical totals are preserved; original item unit prices, actual delivery dates and purchase channels were not supplied.

## Business rules

- Only active products with positive stock are offered. Coming-soon/discontinued products are not presented as available.
- Only active promotions count. Promotional prices and 5% Pix discount do not stack.
- Multiple simultaneous active promotions for one product require confirmation rather than an arbitrary winner.
- Specific installment bands take precedence over the general summary table. Under-R$50 multi-installment purchases require staff confirmation.
- The exact R$500 local-shipping boundary is unspecified and requires confirmation.
- Relevant product-specification conflicts are preserved and withheld from confident technical claims; unaffected prices and stock can still be answered.
- Refund eligibility needs purchase channel and actual receipt date. Expected delivery is not treated as receipt. No refunds are executed.

See [assumptions](docs/assumptions.md) for explicit interpretations.

## Meta official API

See [Meta setup](docs/meta_setup.md). Keep `META_DRY_RUN=true` until intentional live testing.

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8023
# In a separate terminal with the same environment:
python -m src.worker
```

Endpoints: `GET /health`, `GET /webhook`, `POST /webhook`. The POST validates HMAC-SHA256 over raw bytes, filters the configured phone/WABA, persists inbound message IDs and ignores status notifications as user messages. Messages from multiple entries are supported. The worker sends to the trusted inbound sender only.

Free-text output is blocked at/after 24 hours from the triggering customer message. This conservative implementation does not extend an older job's deadline using a newer message. Outside the window, the worker records `blocked`; it does not automatically choose a template. A separate explicit template method accepts only an operator-confirmed approved template. There is no automatic unsolicited contact.

Queue states: pending, processing, sending, sent, simulated, blocked, failed, uncertain. Transient pre-send failures/rate limits have bounded retries. A crash during send, timeout or partial multi-part delivery becomes `uncertain` and requires manual review; no claim of exactly-once external delivery. Failed/uncertain jobs block later messages in the same session until reviewed. Other conversations continue. Inbound bodies persist locally; implement retention/encryption before real deployment.

## Docker

```bash
docker compose up --build
```

Compose runs an initialization job, local UI, API and one worker against a named volume. API/UI ports bind to loopback on the host. A verified HTTPS reverse proxy/tunnel is needed for Meta callbacks. The worker needs configured LLM credentials. No credentials are copied into images. Docker configuration is supplied but Docker execution was not validated in the build environment.

## Validation

```bash
python -m pytest -q
python notebooks/01_validacao_completa.py
```

Open `notebooks/01_validacao_completa.ipynb` in Jupyter/VS Code for **25 numbered Python blocks**. The paired `.py` uses `# %%` cells and is the source of truth. Rebuild the notebook with `python notebooks/build_notebook.py`. No manual JSON editing is needed.

Deterministic tests use temporary databases and HTTP/model test doubles. No WhatsApp messages are sent by default. Executed evidence is in `docs/test_results.txt`, `docs/validation_results.json` and the executed notebook. The live LLM block requires `RUN_LIVE_LLM=true`, a key and a model. It checks grounded scenarios and reports separately. The real Meta block additionally requires `RUN_LIVE_META=true`, `META_DRY_RUN=false`, a confirmed approved template and the exact interactive confirmation `SEND`. It sends one real template and does not prove webhook reception end to end.

See [evaluation](docs/evaluation.md), [architecture](docs/architecture.md), and [examples](examples/README.md). Conversation examples are explicitly scripted model simulations with real tool executions, not fabricated live model transcripts.

## Security and limitations

- Order authorization comes from backend session context. Text entered by a user cannot set `customer_id`.
- Meta sessions start anonymous. Production operators must establish a verified binding through a trusted identity process; matching a typed phone number is insufficient. No OTP provider is implemented.
- The knowledge retriever has no customer/order records. SQL tools enforce ownership even under prompt-injection attempts.
- Prompt-based scope/style/injection behavior still needs real LLM adversarial evaluation. Logs omit message bodies, keys and personal arguments; SQLite history is not encrypted.
- Single-process local UI and one worker are the supported baseline. Lease duration is 600 seconds; distributed locking, heartbeat and horizontal scaling are future work.
- No actual stock reservation, checkout, carrier tracking API, production login, outbound human notification, calendar/holiday service, media understanding or automated template approval.
- The UI shows at most the last 24 messages for context. Add retention, summarization and operational review tooling for production.
- Graph API version must be explicitly selected in the Meta dashboard; documentation retrieval was rate-limited, so no unverified default is shipped.

## AI assistance and provenance

This project was built with ChatGPT/Codex assistance for architecture, implementation, test authoring and documentation, following the candidate's project structure and supplied challenge materials. Tool execution was used for validation; mocked and live results are distinguished. The candidate should review and understand the code, configure accounts and run live evaluations before submission. No claim of unaided authorship is made.

The included Git history records real incremental build stages using `Project Builder <builder@example.invalid>`, not the candidate's identity. Inspect with `git log --oneline`. The repository has not been published and no submission was sent. Preserve this history when publishing; stop modifying the submitted repository at the actual submission cutoff.

Deliverables requested by the recruiter (English PDF/Google Forms) and challenge (public repository/email link) should both be addressed by the candidate. `docs/technical_summary.pdf` is an English draft; repository URL remains intentionally unset until publication.

## Project 23 port allocation

Local UI: 8523. Meta webhook API: 8023. CLI, worker and SQLite do not expose listening ports. Compose project name is `emporio_musica_23`; its named volume is isolated from other Compose projects. The Meta callback is `/webhook` behind HTTPS, normally external port 443. Existing tunnel/reverse-proxy targets must point to local port 8023. Availability on the operator computer has not been checked.

### Python 3.10 migration

Streamlit is pinned to 1.65.0 (the next minor dropped Python 3.10). Docker, notebook metadata and runtime checks target Python 3.10. `tzdata` is an explicit dependency for Windows ZoneInfo support. Keep project ports 8523/8023 and Compose name `emporio_musica_23`. Dependencies and the full test suite are revalidated in an isolated CPython 3.10 environment.
