# Usage

How to set up and run the AI Companion app locally. See `SPEC.md` for the product design and
`.claude`-tracked plan history for what's built vs. deferred — the short version: this is a
walking-skeleton increment. One hardcoded persona, one provider (Claude), no mode switching, no
accounts, no database. Enough to send a message and get a real streamed reply.

## Prerequisites

- Python 3.10+
- Node 18+
- An Anthropic API key — create one at https://console.anthropic.com/settings/keys

## One-time setup

```bash
cd "AI companion/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# edit backend/.env and replace sk-ant-your-key-here with your real key

cd ../frontend
npm install
```

## Running it

**Option A — one command, one terminal:**

```bash
cd "AI companion"
./dev.sh
```

Starts both servers, prints their URLs, stops both on Ctrl+C. It also checks for the common
setup mistakes below before starting anything.

**Option B — manual, two terminals** (useful if you want to see each server's logs separately,
or restart one without the other):

```bash
# terminal 1 — backend
cd "AI companion/backend"
source .venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000
```

```bash
# terminal 2 — frontend
cd "AI companion/frontend"
npm run dev
```

Either way: open **http://localhost:5173**, type a message, hit Send.

## Running tests

```bash
cd "AI companion/backend"
source .venv/bin/activate
pytest
```

Frontend has no test suite yet (out of scope for this increment); `npm run build` type-checks it.

## Troubleshooting

**`ERROR: [Errno 48] Address already in use`**
Something is already listening on that port — usually a dev server from an earlier session that
didn't get stopped. Find and stop it:
```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN   # or :5173 for the frontend
kill <PID>
```

**`cd: no such file or directory: frontend`**
You ran `cd frontend` from inside `backend/` instead of the project root. `backend/` and
`frontend/` are siblings — `cd ..` first, or open a fresh terminal at the project root.

**Chat returns a 401 / "invalid x-api-key" error in the UI**
`backend/.env` still has the placeholder key, or an invalid one. Edit `backend/.env`, set a real
`ANTHROPIC_API_KEY`, then restart the backend (it only reads `.env` at startup, so `--reload`
picking up code changes won't pick up a `.env` edit — stop it with Ctrl+C and rerun).

**Server won't start at all, backend terminal shows a `ValidationError` about `anthropic_api_key`**
`backend/.env` is missing entirely, or missing that field. `cp backend/.env.example backend/.env`
and fill in your key. This is the app's fail-fast check — it refuses to start rather than fail
obscurely on the first chat request.