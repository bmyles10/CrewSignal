# CrewSignal — Manual Testing Guide

Four ways to test the system in VS Code without Claude Code.

---

## Method 1 — VS Code Testing Panel (easiest)

VS Code has a built-in test runner that reads your pytest suite and shows pass/fail visually.

**Setup (one-time):**
1. Open the Command Palette: `Ctrl+Shift+P`
2. Type **"Python: Configure Tests"**
3. Select **pytest**
4. Point it at the `tests/` folder

After setup, a **beaker icon** appears in the left sidebar. Click it to see every test listed by name.

**Running tests:**
- Hit the **play button** at the top to run all tests
- Click the **play button next to a single test** to run just that one
- Right-click any test and select **"Debug Test"** to step through it line by line with breakpoints

The debug option is especially useful when something fails — you can pause execution and inspect exactly what's in the database at each step.

---

## Method 2 — Swagger UI (test the live API visually)

FastAPI auto-generates an interactive API explorer at `/docs`. No extra tools needed.

**Start the server:**
```powershell
cd c:\CrewSignal
.\.venv\Scripts\python.exe main.py
```

**Then open in your browser:**
```
http://localhost:8000/docs
```

You'll see every endpoint laid out with forms to fill in. To test the webhook:
1. Click `POST /api/v1/webhooks/job-completed`
2. Click **"Try it out"**
3. Add your `X-Api-Key` in the header field
4. Paste a payload into the body
5. Click **Execute**

You'll see the real response, status code, and campaign ID returned live.

Works the same way for the `/optout` endpoint — click, fill in, execute.

---

## Method 3 — PowerShell curl commands

Fire requests directly from the VS Code terminal while the server is running. Useful for quickly reproducing specific scenarios.

**Start the server first:**
```powershell
cd c:\CrewSignal
.\.venv\Scripts\python.exe main.py
```

**Valid webhook (should return 202 accepted):**
```powershell
$headers = @{ "X-Api-Key" = "your-real-api-key"; "Content-Type" = "application/json" }
$body = '{"job_id":"JOB-001","customer_name":"John Smith","customer_phone":"+16155551234"}'
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/webhooks/job-completed" -Headers $headers -Body $body
```

**Duplicate webhook (send the same job_id twice, second should return "duplicate"):**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/webhooks/job-completed" -Headers $headers -Body $body
```

**Missing API key (should return 401):**
```powershell
$body = '{"job_id":"JOB-002","customer_name":"Jane Smith","customer_phone":"+16155559999"}'
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/webhooks/job-completed" -Body $body -ContentType "application/json"
```

**Wrong API key (should return 401):**
```powershell
$bad_headers = @{ "X-Api-Key" = "not-a-real-key"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/webhooks/job-completed" -Headers $bad_headers -Body $body
```

**Register an opt-out:**
```powershell
$optout_body = '{"phone":"+16155551234"}'
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/api/v1/optout" -Headers $headers -Body $optout_body
```

**Health check:**
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

**Check what landed in the database:**
```powershell
.\.venv\Scripts\python.exe peek_db.py
```

---

## Method 4 — Run specific tests from the terminal

Run slices of your test suite instead of everything at once. Useful when you're focused on one area.

**All tests:**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

**One test file:**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_webhooks.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_worker.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_sms_twilio.py -v
.\.venv\Scripts\python.exe -m pytest tests/test_optout.py -v
```

**One specific test by name:**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_webhooks.py::test_duplicate_webhook_returns_202_without_double_insert -v
```

**Show print() output during tests (useful for tracing worker behavior):**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v -s
```

**Run only tests matching a keyword:**
```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v -k "optout"
.\.venv\Scripts\python.exe -m pytest tests/ -v -k "duplicate"
```

---

## Recommended day-to-day workflow

| Goal | Best method |
|---|---|
| Verify nothing broke after a code change | VS Code test panel (Method 1) |
| See the live system working end-to-end | Swagger UI (Method 2) |
| Reproduce exactly what a CRM would send | PowerShell curl (Method 3) |
| Debug a failing test step by step | VS Code debug mode (Method 1) |
| Focus on one test file quickly | Terminal pytest (Method 4) |
| Check what's in the database | `peek_db.py` (Method 3) |
