# CrewSignal Daily Startup Checklist

## Terminal 1 — Server
- [ ] Open PowerShell, navigate to project: `cd C:\CrewSignal`
- [ ] Activate the virtual environment: `.\venv\Scripts\Activate.ps1`
- [ ] Confirm prompt shows `(venv)` before proceeding
- [ ] Start the server: `python main.py`
- [ ] Wait for both of these lines to appear:
  - `Uvicorn running on http://0.0.0.0:8000`
  - `[WORKER] Durable SMS dispatch worker started.`
- [ ] Leave this window open — never type in it while the server is running

## Terminal 2 — Commands
- [ ] Open a second PowerShell window
- [ ] Navigate to project: `cd C:\CrewSignal`
- [ ] Activate the virtual environment: `.\venv\Scripts\Activate.ps1`
- [ ] This is your working terminal for manage.py commands and test webhooks

## Terminal 3 — ngrok (only needed if testing public webhooks)
- [ ] Open a third PowerShell window
- [ ] Run: `C:\Users\BrandonMyles\Downloads\ngrok.exe http 8000`
- [ ] Copy the `https://...ngrok-free.app` URL from the Forwarding line
- [ ] Note: ngrok gives you a **new URL every time** — update any webhook configs that use the old one

---

## Quick Reference

**Your API key** (MylesHouse Tech Test tenant):
```
iaVxS15xbJrVUBsBn9VDeXWqd6qbzAz75-ZRIKIzAbg
```
> Run `python manage.py list-tenants` if this ever stops working — the key changes when you delete and re-provision the database.

**Send a test webhook** (paste in Terminal 2, increment job_id each time):
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Api-Key" = "iaVxS15xbJrVUBsBn9VDeXWqd6qbzAz75-ZRIKIzAbg"
}
$body = @{
    job_id = "test-job-001"
    customer_name = "Brandon"
    customer_phone = "+16157963530"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/webhooks/job-completed" -Method POST -Headers $headers -Body $body
```

**Health check** (confirm server is alive):
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

**Peek at the database:**
```powershell
python peek_db.py
```

---

## Common Problems

| Problem | Fix |
|---|---|
| `No module named 'uvicorn'` | You forgot to activate venv — run `.\venv\Scripts\Activate.ps1` first |
| `401 Unauthorized` | API key changed — run `python manage.py list-tenants` to get current key |
| `table has no column` error | Database is stale — delete `database\crewsignal.db` and re-provision |
| Worker logs "Mock SMS sent" | `USE_MOCK_SMS=True` in `.env` — flip it to `False` |
| ngrok URL stopped working | ngrok generates a new URL each session — restart ngrok and use the new URL |
