# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AI Companion: a multi-mode companion app (companionship/emotional-support, roleplay, romantic/intimate).
The current code is a **walking-skeleton increment**, not the full product: one hardcoded persona, no
database, no auth, no persisted conversation history. Full product design lives in `SPEC.md` (authoritative
v1 spec — read this first for anything touching personas, memory, safety, or access control); `VISION.md`
is the superseded rough draft kept for historical context only. `USAGE.md` has local setup/run/troubleshooting
instructions — don't duplicate them here, refer to that file.

## Lessons
[Here claude code will write learned lessons for each session if any. Lessons are things that might usefull in the feature]

## Commands

Backend (`backend/`, Python 3.10+, venv at `backend/.venv`):
```bash
source .venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000   # run
pytest                                                  # run all tests
pytest tests/unit/test_chat_service.py                 # run a single test file
pytest tests/unit/test_chat_service.py::test_name -v   # run a single test
```

Frontend (`frontend/`, Node 18+):
```bash
npm run dev       # dev server at http://localhost:5173
npm run build     # tsc -b type-check + vite build (there is no frontend test suite yet)
```

Both at once from the repo root: `./dev.sh` (checks for common setup mistakes — missing venv,
missing `.env`, placeholder API key — before starting either server).

## Architecture

### Provider abstraction — the load-bearing seam

The single most important constraint in this codebase (SPEC.md §2): **no code outside
`src/services/providers/` may know which LLM backend a request is using.**

- `services/providers/base.py` defines `CompanionModelProvider.stream_reply(messages, persona, config) -> AsyncIterator[str]`.
  Every backend (Claude, OpenRouter, OpenAI, Ollama) implements this and only this.
- `services/providers/registry.py` is a Factory + Strategy: `ProviderId` enum → `build_provider()` dict
  lookup. Adding a backend means one new `CompanionModelProvider` subclass plus one registry entry —
  no other call site changes.
- `services/provider_router.py::ProviderResolver` is the only other class allowed to know the model
  catalog / mode-routing rule. It resolves `(model_id, persona)` → `(provider, provider_config, is_uncensored)`
  by precedence: explicit `model_id` > persona mode (`"intimate"` routes to `Settings.intimate_mode_model_id`)
  > `Settings.default_model_id`.
- `ChatService` (services/chat_service.py) only ever sees the resolver's output — never a provider identity
  directly. `api/routes/chat.py`, `models/chat.py`, and the frontend only ever see a `model_id` string.
- The model catalog is a hardcoded list in `config.py::_default_catalog()` (a DB-backed catalog is future
  work). `Settings.enabled_catalog()` filters out entries whose provider lacks credentials, so the API/UI
  never offer a model that would fail on first use.

### Media generation — the same seam, once per modality

Image and video generation mirror the text provider stack rather than extending it, because
generation is single-shot while chat is streamed:

- `services/image_providers/base.py::ImageGenerationProvider.generate_image(prompt, config) -> str`
  and `services/video_providers/base.py::VideoGenerationProvider.generate_video(...)`.
- Each has its own registry (Factory + Strategy, same dumb-dict shape as
  `services/providers/registry.py`) and its own credential-gated catalog in `config.py`
  (`enabled_image_catalog()` / `enabled_video_catalog()`).
- Each has a resolver — `services/image_router.py`, `services/video_router.py` — taking an
  optional `model_id` from the request, falling back to the configured default.
- There is deliberately **no "generate image" button**: intent is inferred from the message
  text by `services/image_intent.py` / `services/video_intent.py`, and `ChatService` branches
  to the media path before calling any LLM.
- Adding a backend means one new provider subclass plus one registry entry — no other call
  site changes. `ComfyUIVideoProvider` is the exception worth reading first: it speaks
  ComfyUI's real three-step API (submit graph, poll, fetch) and runs a user-exported workflow
  with a `{prompt}` placeholder, because workflow graphs differ per model and per version.

### Persona / system prompt layer

`personas/base.py` is a placeholder for the full per-user/starter/custom persona system in SPEC.md §3.
Only one hardcoded `PersonaConfig` exists today (constructed in `ChatService.stream_response`). Key
behavior to preserve when extending this: `compose_system_prompt` selects between
`BASE_SYSTEM_INSTRUCTIONS` and `INTIMATE_MODE_SYSTEM_INSTRUCTIONS` based on `persona.mode`, and this
prefix is designed to be un-overridable by the persona's own instruction text — that property must
survive any future persona-authoring feature.

### Safety layer

`services/safety/uncensored_guard.py::UncensoredSafetyGuard` is an independent check applied **only**
when the resolved provider is `uncensored=True` in the catalog (Claude is trusted to self-moderate via
its own tuning; uncensored open-weight models are not — SPEC.md §5). It's wired into `ChatService`, not
into individual providers, and runs both on the incoming request (`check_request`) and on the
accumulating output stream (`wrap_stream`), raising `SafetyInterventionError` on a crisis trigger-phrase
match. Currently keyword-based by design (placeholder for a classifier — see the module docstring); keep
new trigger logic in this module rather than scattering checks elsewhere.

`services/safety/image_content_guard.py` and `video_content_guard.py` are the media
counterparts, and differ in one important way: they run on **every** generation prompt
regardless of backend, because image/video generation has no LLM in the loop to self-moderate.
They are gated on the resolved *text* provider's `is_uncensored`, so picking an uncensored
image backend never widens what the conversation's mode allows.

### Streaming

Chat replies stream via SSE. `ChatService.stream_response` yields SSE-framed `StreamChunk`s
(`utils/sse.py::format_sse`): zero-or-more `TOKEN` chunks, then exactly one `DONE`, or one `ERROR` if
generation/safety-check fails mid-stream. A media turn instead yields exactly one `IMAGE` or
`VIDEO` chunk (a URL or `data:` URI) followed by `DONE` — the frontend renders these as `<img>`
/ `<video>` and strips them from the history it resends. The frontend (`api/chatClient.ts`) deliberately uses `fetch` +
manual `ReadableStream` parsing instead of `EventSource`, since the request needs a POST body
(conversation history) that `EventSource` can't express.

### Config / fail-fast

`config.py::Settings` (Pydantic v2 `BaseSettings`, loaded from `backend/.env`) requires
`ANTHROPIC_API_KEY` with no default — construction raises `ValidationError` if unset.
`main.py::create_app()` calls `get_settings()` at import time specifically so this surfaces as an
immediate, readable startup error rather than an obscure failure on the first chat request. Preserve
this pattern for any new required setting.

## Project-standard conventions already in force here

Pydantic v2 everywhere for data contracts (no raw dicts across module boundaries), full type annotations,
Google-style docstrings — consistent with global standards; this codebase is a good reference example of
them (see `config.py`, `services/provider_router.py`).
