# AI Companion — Backend

FastAPI service exposing a streaming chat endpoint backed by the Claude API. This is the walking-skeleton
increment: no database, no auth, no persisted personas — see the root `SPEC.md` for the full v1 design and
`ChatService`/`personas/base.py` docstrings for where those future layers plug in.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

## Run

```bash
source .venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000
```

## Test

```bash
source .venv/bin/activate
pytest
```
