# SMS Security Lab

A local, university-lab-safe simulator that demonstrates the *shape* of a
typical SMS-sending backend — API → provider abstraction → delivery event →
inbox → logging — **without ever sending a real SMS or making any outbound
network request.**

## What this is / is not

- ✅ A local Flask + vanilla JS dashboard for teaching how an SMS pipeline
  is usually structured.
- ✅ Every "delivery" is a random, in-memory simulation.
- ❌ No SMS gateway (Twilio, Vonage, MessageBird, SMPP, etc.) integration.
- ❌ No credentials, API keys, or telecom config anywhere in the code.
- ❌ No bulk sending, no repeat/count parameters, no multi-recipient
  sending. Each request creates **exactly one** simulated message.

## Features

- Single-message "SMS Mode" panel with client- and server-side validation
- In-memory Inbox showing simulated delivered messages
- Event Log table (timestamp, mode, masked recipient, status, message ID,
  provider)
- Live-updating statistics (attempts / delivered / failed / messages)
- Phone numbers are masked everywhere except the input field while typing
- "Clear Lab Data" button with confirmation
- Architecture panel for viva/demo purposes
- Automated pytest suite, fully offline

## Architecture

```
Browser
  ↓
Flask REST API
  ↓
SMS Provider (local mock, no network)
  ↓
Delivery Simulator (weighted random outcome)
  ↓
Inbox
  ↓
Event Logger
```

`SmsProvider.send_message()` never opens a socket. It returns a dict with a
randomly-chosen `DELIVERED`/`FAILED` status (95% / 5% by default) purely to
demonstrate both outcome paths in the UI.

## Project structure

```
sms_security_lab/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env.example
│
├── templates/
│   └── index.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
└── tests/
    └── test_api.py
```

## Windows installation (PowerShell)

### Option A — without activating the virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

### Option B — activating the virtual environment

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Then open your browser to:

```
http://127.0.0.1:5000
```

`127.0.0.1` (loopback) means the server is reachable **only from this
computer** — not from other machines on the network.

## How to test

With the virtual environment active:

```powershell
python -m pytest tests/ -v
```

The tests use Flask's built-in test client and never touch the network.

## How the Inbox works

1. You submit a recipient + message through the "SMS Mode" panel.
2. The frontend POSTs JSON to `/api`.
3. The backend validates the input, then asks the local `SmsProvider` to
   "send" the message. The provider immediately returns a simulated
   result (`DELIVERED` or `FAILED`) — no network call is made.
4. Every attempt is logged as one row in the Event Log.
5. Only `DELIVERED` attempts create an Inbox item.
6. Statistics update from the same response — no page reload needed.

## API documentation

### `GET /`
Returns the dashboard HTML page.

### `POST /api`
Body:
```json
{ "number": "8801700000000", "message": "test message" }
```
Success response:
```json
{
  "ok": true,
  "event": { "...": "..." },
  "stats": { "attempts": 1, "delivered": 1, "failed": 0, "messages": 1 },
  "inbox": [ { "...": "..." } ]
}
```
Error response (HTTP 400):
```json
{ "ok": false, "error": "Please enter a recipient." }
```
Creates exactly one simulated event per call. There is no bulk, batch,
count, or repeat parameter — sending 100 messages requires 100 separate
requests, each triggered by a separate user click.

### `GET /api/state`
Returns the full current state:
```json
{ "events": [...], "inbox": [...], "stats": {...} }
```

### `POST /api/clear`
Clears all in-memory data. Returns `{ "ok": true }`.

## Viva explanation

This project demonstrates the standard layered architecture behind an
SMS-sending feature — a REST endpoint, a provider abstraction that hides
the delivery mechanism from the rest of the app, an event/audit log, and a
user-facing inbox — while keeping the "provider" entirely local. In a real
product, `SmsProvider.send_message()` would call out to a gateway like
Twilio; here it returns a simulated result so the architecture can be
studied and demoed safely, with no real messages, credentials, or network
traffic involved. Phone number masking and single-message-per-request
design illustrate basic data-minimization and abuse-prevention principles
that a production system would also need.

## Troubleshooting

- **`python` not found**: use `py` instead on Windows, or make sure Python
  3.10+ is installed and on PATH.
- **Execution policy error when activating the venv**: run
  `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first (only
  affects the current PowerShell session).
- **Port 5000 already in use**: stop whatever else is using it, or change
  the port in the `app.run(...)` call at the bottom of `app.py`.
- **Page loads but styling looks broken**: make sure you're running the
  app from the project root so Flask can find `static/` and `templates/`.





  ## Demo Photo can be seen here: [Demo.png](https://github.com/byishmam/SMS-Security-Lab/blob/main/Demo.png)
