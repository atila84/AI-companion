---
name: ai-companion-conventions
description: Project conventions for the AI Companion repo — file layout, testing patterns, Pydantic model placement, provider/registry patterns, frontend structure, and known doc gaps. Load before adding a new LLM/image provider, writing backend tests, adding a Pydantic model, touching frontend components/types, or editing config/.env settings.
---

# AI Companion conventions

Complements `CLAUDE.md` (architecture map). This is the concrete stuff you'd otherwise have to
re-derive by reading many files. Read `CLAUDE.md` first for *why* things are shaped this way;
this file is for *where things go* and *what pattern to copy*.

## Layout gap CLAUDE.md doesn't cover: image generation is a second full provider stack

`services/image_providers/` mirrors `services/providers/` exactly but is undocumented in
CLAUDE.md: its own ABC (`ImageGenerationProvider`), own `registry.py` (`ImageProviderId` enum +
`build_image_provider()`), own resolver (`services/image_router.py`), own intent detector
(`services/image_intent.py`, regex-based "is this an image request?"), own safety guard
(`services/safety/image_content_guard.py`), own catalog (`ImageCatalogEntry` in `config.py`).
There is no separate image API route — generation is triggered implicitly inside
`/api/chat/stream` via `image_intent.py`, and surfaced as a `StreamChunkType.IMAGE` chunk.
Treat this directory as equally load-bearing as `services/providers/`, not a side feature.

Stray note: `__pycache__` may contain compiled `.pyc` files referencing `video_router`,
`video_service`, `replicate_provider`, etc. These are leftovers from reverted local
experimentation, never committed. If you go looking for a "video" or "replicate" feature because
of a `.pyc` file, stop — it doesn't exist in source.

## Testing

- **No `conftest.py` anywhere in the repo** — this is deliberate, not an oversight. Fixtures
  (`settings`, `resolver`, `guard`, `messages`, `persona`, `provider_config`, ...) are redefined
  locally in each test file that needs them. Don't add a `conftest.py`.
- One test file per source module, name mirrors the module path:
  `services/chat_service.py` → `tests/unit/test_chat_service.py`.
- Test function names are full sentences: `test_<behavior>_<expected_outcome>`, e.g.
  `test_resolve_raises_for_unknown_explicit_model_id`. Never numbered (`test_1`).
- **Never `unittest.mock`/`MagicMock`.** Hand-write duck-typed fake classes matching the exact
  shape of the SDK object being replaced:
  - Anthropic: `_FakeAsyncAnthropic` → `_FakeMessages` → `_FakeStreamContextManager`
    (`__aenter__`/`__aexit__`) → `_FakeTextStream` (`__aiter__`), mirroring
    `client.messages.stream(...)`.
  - OpenAI-shaped: `_FakeAsyncOpenAI` → `_FakeChat` → `_FakeCompletions.create()` →
    `_FakeChatCompletionStream`, using `SimpleNamespace(choices=[SimpleNamespace(delta=...)])`.
  - Service-level tests (`ChatService`, routes) fake the resolver interface directly
    (`_FixedResolver`, `_FakeResolver`, `_StubImageResolver`) rather than the network client.
- Settings in tests: `monkeypatch.setenv(...)` then construct with
  `Settings(_env_file=None)  # type: ignore[call-arg]` to bypass the real `.env`.
- `pyproject.toml` sets `asyncio_mode = "auto"` — don't add `@pytest.mark.asyncio`.
- Integration tests (`tests/integration/`, currently just `test_chat_endpoint.py`) hit the real
  ASGI app via `httpx.ASGITransport` and only override `app.dependency_overrides[get_provider_resolver]`
  — this is exactly why `api/deps.py` centralizes DI construction (see its docstring).
- Every test module opens with a one-line docstring naming what's under test, often with an
  explicit "no real network call" reassurance.

## Pydantic models: NOT centralized in `models/`

Placement depends on role:

| Kind | Lives in | Naming |
|---|---|---|
| API/wire contracts | `models/chat.py` | `<Noun>Request`, `<Noun>Chunk` |
| Config/catalog rows | `config.py` (next to `Settings`) | `<Noun>Entry` |
| Per-subsystem request config | next to its ABC (`services/providers/base.py`, `services/image_providers/base.py`) | `<Noun>Config` |
| Persona | `personas/base.py` | — |

- Document fields with a class-level Google-style `Attributes:` docstring block, **not**
  `Field(description=...)`. `Field()` is reserved for actual constraints (`gt=0`, `ge=1`, etc.).
- No `@field_validator`/`@model_validator` anywhere currently — validation is either type-level
  (`Literal[...]`, enums) or procedural (plain methods raising a domain exception, e.g.
  `Settings.catalog_entry` raising `ProviderConfigError`). Introducing a Pydantic validator would
  be a new pattern — fine if warranted, but note it's a deviation.
- Enums are always `class X(str, Enum)`, never plain `Enum`/`IntEnum`.

## Adding a new chat provider (`services/providers/`)

1. OpenAI-wire-compatible backend → subclass `OpenAICompatibleProvider`, add **zero logic** —
   just a docstring and maybe a base-URL constant (see `openrouter_provider.py`, `ollama_provider.py`).
   All request-building/streaming/error-wrapping is inherited.
2. Not OpenAI-shaped → implement `CompanionModelProvider.stream_reply` directly, per
   `claude_provider.py` (async-context-manager stream, wraps `anthropic.APIError` → `ProviderAPIError`).
3. Add one `_build_<name>(settings)` factory in `registry.py` that raises `ProviderConfigError`
   if credentials are missing, and one entry in `_PROVIDER_FACTORIES`.
4. Reuse the `@lru_cache`-decorated module-level client constructor pattern
   (`_anthropic_client`, `_openai_client`) instead of constructing SDK clients inline — clients
   are always built in the registry or `api/deps.py`, never inside the provider class itself.
5. `registry.py` imports `Settings` only under `if TYPE_CHECKING:` (forward-ref string
   `"Settings"` in signatures) to avoid a circular import with `config.py`. Replicate this if a
   new registry-like module needs to type-hint `Settings`.

`services/image_providers/` follows this exact same recipe (own `ImageProviderId`,
`_IMAGE_PROVIDER_FACTORIES`, `build_image_provider()`) — the only difference is
`generate_image(prompt, config) -> str` is single-shot, not a stream.

## Error handling

Each subsystem gets its own `exceptions.py` with a base class plus 1-2 subclasses:
`ProviderError > {ProviderConfigError, ProviderAPIError}`. `SafetyInterventionError` is
deliberately **not** a `ProviderError` subclass — a safety interception is a policy decision, not
a backend failure. `ChatService` catches `(ProviderError, SafetyInterventionError)` together at
the streaming boundary and converts to `StreamChunk(type=ERROR, content=str(exc))` — never let
either propagate as an unhandled 500.

## Docstrings

- Google-style `Args:`/`Returns:`/`Yields:`/`Raises:` on every public function/class (private
  one-liner factories like `_build_claude` can skip it).
- Module-level docstrings explain **why** the module is shaped this way, not what it does
  (e.g. "the single most important constraint...", "deliberately a dumb dict lookup, not plugin
  discovery").
- Any module standing in for unbuilt SPEC.md functionality says so explicitly using the literal
  word "placeholder" and cross-references the SPEC.md section (`personas/base.py`,
  `uncensored_guard.py`, `image_content_guard.py`, `image_intent.py`). Keep this label on new
  stand-in code rather than presenting it as finished.
- Provider/image-provider docstrings note *where* their client is constructed (registry or
  `api/deps.py`, never the class itself) — keep this note when adding new ones.

## Frontend (`frontend/src`)

- Components: PascalCase filename = exported function name, `export function X(props): React.JSX.Element`
  (not `React.FC`), flat in `components/` (no subdirectories yet). State stays lifted in
  `ChatWindow.tsx`; other components are props-in/callback-out.
- API calls centralized in `api/chatClient.ts` — plain `fetch`, JSDoc `@param`/`@returns`/`@yields`
  mirroring the backend's Google-style docstrings. `streamChatReply` is an `async function*`
  parsing SSE frames manually off `response.body.getReader()` (not `EventSource`, since the
  request needs a POST body).
- `types/chat.ts` is a **hand-maintained mirror** of backend Pydantic models — no codegen. Any
  change to `models/chat.py` or the catalog models in `config.py` must be manually mirrored here.
- Styling: one global `styles/index.css`, BEM-ish `block`/`block--modifier` classes (`.message`,
  `.message--user`, `.chat-window`). No CSS modules, Tailwind, or styled-components — don't
  introduce a second styling system.
- No frontend test suite by design; `npm run build`'s `tsc -b` type-check is the only check.

## Config / `.env` — known gap

`Settings` (`config.py`) reads `backend/.env` via `pydantic_settings.BaseSettings`,
`UPPER_SNAKE_CASE` vars mapped to lowercase fields.

**`backend/.env.example` is currently stale** — it only lists `ANTHROPIC_API_KEY`,
`CLAUDE_MODEL`, `CORS_ALLOW_ORIGINS`. It's missing `OPENROUTER_API_KEY`, `OPENAI_API_KEY`,
`OLLAMA_BASE_URL`, `DEFAULT_MODEL_ID`, `INTIMATE_MODE_MODEL_ID`, and every image-subsystem
setting (`automatic1111_base_url`, `default_image_model_id`, `image_model_catalog`). A fresh
`cp .env.example .env` per USAGE.md silently under-configures the app. **When adding a new
`Settings` field, update `.env.example` in the same change** so this gap doesn't grow further.

## Import ordering

stdlib → third-party (`anthropic`, `openai`, `httpx`, `fastapi`, `pydantic`) → local `src.*`,
alphabetized within each group, in every file.

## Which doc answers which question

- **SPEC.md** — authoritative v1 product spec. Read first for anything about personas, memory,
  safety, modes, or access control.
- **VISION.md** — superseded rough draft. Historical context only, not current.
- **CLAUDE.md** — architecture map of what's actually built. This skill complements it, doesn't
  replace it.
- **USAGE.md** — local setup/run/troubleshooting only.
