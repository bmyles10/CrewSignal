# CrewSignal — Claude Code Instructions

## What this project is

CrewSignal is a vertical SaaS for field service contractors (roofing, HVAC, plumbing, electrical, landscaping). Its sole purpose: automatically send a Google Review SMS when a job is marked complete inside the contractor's CRM.

One integration. One workflow. One outcome. Do not expand scope beyond this.

---

## Architecture decisions (locked)

### Database
- **SQLite with WAL mode** through beta (first ~5 paying clients)
- WAL mode must be enabled at engine creation: `PRAGMA journal_mode=WAL`
- **Switch to managed Postgres** (Render or Railway) the day the first paying client signs
- All models and queries must be written Postgres-compatible — no SQLite-only types or tricks
- Connection string lives in one place: `app/core/db.py`

### SMS
- `BaseSMSAdapter` (abstract) in `app/adapters/sms_base.py` is the contract — never bypass it
- `MockSMSAdapter` is the default for local dev — tests must NEVER hit real Twilio
- Adapter is selected by config/env variable, not hardcoded
- `sms_twilio.py` wraps sends in `tenacity` with exponential backoff

### Queue
- **No FastAPI BackgroundTasks for SMS sending** — they silently drop on restart/deploy
- Webhook writes a `ClientCampaign` row with `delivery_status="pending"` and returns 202
- A **separate worker loop** polls for `pending` rows, sends, updates to `sent` or `failed`
- Always read the adapter return value and update `delivery_status` + `updated_at`

### Auth
- Every webhook must carry a valid API key checked against `Tenant.api_key`
- Invalid or missing key → 401, full stop
- Auth lives in `app/api/deps.py` as a FastAPI dependency
- `tenant_id` must be confirmed against a real, active Tenant row — never trust the payload value alone

### Idempotency
- Before inserting a `ClientCampaign`, check for existing row matching `(tenant_id, provider, provider_event_id)`
- Duplicate found → return 202 immediately, set status `"duplicate"`, send nothing
- CRMs retry aggressively — without this, customers get spammed and Twilio numbers get flagged

---

## Tech stack

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| ORM | SQLModel |
| DB (beta) | SQLite + WAL |
| DB (paid) | PostgreSQL |
| SMS | Twilio via `sms_twilio.py` |
| Retry | tenacity |
| Config | pydantic-settings / `.env` |
| Testing | pytest + pytest-asyncio + httpx |
| Migrations (future) | Alembic |
| Deploy | Docker + Caddy (auto HTTPS) |

---

## Project structure

```
CrewSignal/
├── main.py                   # FastAPI app + lifespan boot
├── CLAUDE.md                 # This file
├── requirements.txt
├── Dockerfile
├── Caddyfile
├── peek_db.py                # Dev diagnostic only
├── app/
│   ├── api/
│   │   ├── deps.py           # API key auth dependency (MUST be implemented)
│   │   └── v1/
│   │       └── webhooks.py   # POST /job-completed
│   ├── adapters/
│   │   ├── sms_base.py       # Abstract base — do not change signature
│   │   ├── sms_mock.py       # Local dev only
│   │   └── sms_twilio.py     # Real adapter with tenacity retry
│   ├── core/
│   │   ├── config.py         # pydantic-settings
│   │   ├── db.py             # Engine + WAL mode + get_session
│   │   └── logger.py         # Structured logging (not yet implemented)
│   └── models/
│       └── db_models.py      # Tenant, ClientCampaign
└── tests/
    ├── conftest.py           # In-memory SQLite test DB
    └── test_webhooks.py
```

---

## Current task priority order

Work through these in sequence. Do not skip ahead to polish.

1. **WAL mode** — add `PRAGMA journal_mode=WAL` to `db.py` engine creation
2. **Real idempotency** — `(tenant_id, provider, provider_event_id)` dedupe before insert
3. **API key auth** — fill `deps.py`, inject into webhook endpoint
4. **Real Pydantic payload** — model actual Jobber `job_complete` webhook shape from their docs
5. **`sms_twilio.py`** — implement with `tenacity` exponential backoff
6. **Durable worker** — replace BackgroundTasks with a polling worker loop
7. **Opt-out handling** — suppression table + check before send + opt-out line in template
8. **Expand tests** — duplicate webhook, invalid key, malformed payload, worker state transitions

---

## Hard rules

- **Never commit `.env`** — repo is public on GitHub
- **Never let tests hit real Twilio** — always use MockSMSAdapter in test context
- **Never skip the auth check** — even in dev, the dependency must be wired
- **Always update `updated_at`** on any status change to a `ClientCampaign`
- **Always return 202** from the webhook endpoint — CRM must get a fast response
- **Do not expand features** until the 8 tasks above are complete and a beta client is live

---

## Testing conventions

- Test DB: in-memory SQLite via `StaticPool` (see `conftest.py`)
- Every test gets a fresh schema, torn down after
- Tests use `httpx.AsyncClient` with `ASGITransport` — no live server needed
- Mark all tests: `@pytest.mark.asyncio`
- A good test verifies the DB row, not just the HTTP status code

---

## Running locally

```bash
# Start the server
python main.py

# Run tests
pytest tests/ -v

# Peek at the database
python peek_db.py

# Health check
curl http://localhost:8000/health
```

---

## What CrewSignal is NOT

- Not a full marketing platform
- Not a multi-channel outreach tool
- Not an all-in-one contractor CRM
- Not a reputation management dashboard

If a feature idea doesn't directly serve "send one review SMS after one completed job," it goes on a future list, not in the codebase.
