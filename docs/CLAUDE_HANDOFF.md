# CrewSignal — Claude Session Handoff

_Last updated: 2026-06-30_

This doc exists so a new Claude session (or Claude Code instance) can get fully caught up on where CrewSignal actually stands, without re-deriving it from scratch. Read this first, then `CLAUDE.md` in the project root for the architecture rules.

## Who's building this

Brandon Myles — solo founder, not a professional developer, operating under MylesHouse Technology (LLC in progress, see task 4.12 in the tracker). He relies on Claude to write, explain, and walk through everything in plain terms. Prefers detailed, step-by-step instructions since he's not a full-time coder. Point him to `STARTUP.md` in the project root first if he asks how to start the server, run a test webhook, or fix a common error — don't re-explain from scratch.

## Where the source of truth lives

- **`CrewSignal_Deployment_Tracker.xlsx`** (project root) — the master task tracker. Every phase, task number, status. Always check this before assuming what's done.
- **`STARTUP.md`** (project root) — daily startup checklist: activating venv, starting the server, sending test webhooks, common errors and fixes.
- **`CLAUDE.md`** (project root) — architecture rules and hard constraints (locked decisions on DB, SMS, queue, auth, idempotency). These override default behavior.

## Real-world status (as of last session)

**A2P 10DLC is APPROVED.** Real Twilio number `+16292891997` is live and carrier-trusted. This is not a toy anymore — real texts have been sent and delivered to Brandon's own phone successfully, confirmed via Twilio Message Logs.

**What's actually been built and tested end-to-end:**
- Full webhook → DB → worker → Twilio → phone pipeline works locally (`python main.py`)
- Confirmed working over the public internet via ngrok (task 3.4)
- Admin CLI (`manage.py`) supports `provision`, `update-tenant`, `list-tenants` — provisioning now accepts `--place-id` (generates the direct Google `writereview` URL) as an alternative to `--review-url`
- Failure alerting is live (task 5.0) — `app/core/alerts.py` sends email via Gmail SMTP when an SMS send fails or the worker crashes. Config lives in `.env` (`ALERTS_ENABLED`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_PASSWORD`, `ALERT_EMAIL_TO`)
- Inbound Twilio SMS webhook exists (`app/api/v1/inbound.py`, task 1.6a) — handles STOP/STOPALL/UNSUBSCRIBE/CANCEL/END/QUIT by looking up the customer's most recent `ClientCampaign` to attribute the opt-out to the correct tenant (since one Twilio number is currently shared across tenants), then writes to the `OptOut` table. Verifies Twilio's request signature using `TWILIO_AUTH_TOKEN` — skips verification only if the token is still the mock value. **This endpoint is NOT yet registered in the Twilio Console** — that's a manual step still pending (see "Known gaps" below).

**There is no live paying client yet.** Everything so far has been Brandon's own test tenant and his own phone number.

## Known gaps / immediate next steps (in tracker order)

1. **Task 1.6b (Pending)** — START/UNSTOP/YES re-opt-in isn't handled yet. Right now if a customer opts out then texts START, Twilio clears its own carrier-level block, but our internal `OptOut` table still has the row — so CrewSignal would keep suppressing them even though Twilio would deliver. Needs the same `inbound.py` webhook extended to detect those keywords and delete the matching row.
2. **Twilio Console webhook registration** — the inbound SMS URL (`/api/v1/webhooks/twilio-inbound`) needs to actually be set as the "A message comes in" webhook on the Twilio phone number config. Requires an active ngrok tunnel (or real deployment) and `PUBLIC_BASE_URL` set in `.env` to match, since signature validation checks the exact URL.
3. **Task 4.12/4.13** — LLC formation, in progress, on Brandon (paperwork, not code).
4. **Task 4.14** — Final compliance go/no-go gate before onboarding any real client.
5. **Phase 5** — Onboard 1-3 free beta clients, watch real jobs run, get one testimonial/proof.

## Gotchas learned the hard way this build

- **Deleting `database/crewsignal.db` and re-provisioning changes the API key.** Every time the DB is wiped, run `python manage.py list-tenants` to get the current key — don't assume the old one still works.
- **The venv must be activated** (`(venv)` prefix in the prompt) or `ModuleNotFoundError` for uvicorn/sqlmodel/etc. This trips Brandon up frequently.
- **`requirements.txt` was originally hard-pinned and had a real dependency conflict** (sqlmodel 0.0.38 requires pydantic >=2.11, but fastapi 0.115 was pinned against pydantic==2.8.2). It's now using `>=` ranges instead of hard pins — don't re-introduce hard pins without checking compatibility.
- **`python-multipart` is required** for FastAPI to parse Twilio's form-encoded inbound webhook payloads — already added to `requirements.txt`, but if a fresh venv is ever rebuilt, confirm it installed.
- **The xlsx tracker file can't be written to while it's open in Excel** — if a save fails with `PermissionError`, ask Brandon to close the file first.
- **ngrok's free tier generates a new URL every time it restarts** — any Twilio console webhook config pointing at an old ngrok URL breaks silently until updated.
- **Only one Twilio number currently serves all tenants** (no per-tenant number yet) — this is why the inbound STOP handler has to infer the tenant from campaign history rather than from the `To` field.

## Tenant / test data notes

- Current test tenant: "MylesHouse Tech Test" — `review_url` points to Brandon's dad's real Google Business Profile (`placeid=ChIJ5fpV8z8DY4gR4JMWaHjDf3s`) as a stand-in real-world test, since his dad may become an actual client later.
- Brandon's wife owns a Square-based salon — flagged as the natural first production client for the *future* Square integration (Phase 8), but Phase 8 isn't built yet. Don't suggest testing against her Square account until 8.1–8.5 exist.
