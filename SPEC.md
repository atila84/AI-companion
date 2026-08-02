# AI Companion — v1 Spec

Companion source-of-truth spec. Resolves the TBDs left open in `VISION.md`. This is a v1 spec for a solo/small-team build — favor the simplest thing that works, architected so the explicitly-deferred features can be added without a rewrite.

## 1. Overview

- Multi-mode AI companion: **companionship/emotional support**, **roleplay & interactive fiction**, and **romantic/sexual/intimate**.
- One companion per user in v1 — a persona (starter or custom), a mode, and the memory/relationship state attached to it.
- Text chat only. Web app, responsive, no native mobile in v1.
- Somewhere accessible (About/Terms page), it must be clearly disclosed that this is an AI, not a person. This is non-negotiable and ships in v1.

## 2. Architecture

- **Backend**: Python + FastAPI. All Pydantic v2 models, typed, Google-style docstrings per project standards.
- **Frontend**: React + TypeScript.
- **Database**: Postgres.
- **Deployment**: single VPS (e.g. Hetzner/DigitalOcean), Docker Compose running FastAPI, Postgres, and the built React app. No managed cloud services in v1 — revisit if traffic justifies the added cost/complexity.
- **Streaming**: chat responses stream token-by-token to the client (SSE or WebSocket), not returned as a single completed message.

### Provider abstraction

The single most important architectural constraint: **no code outside the provider layer knows which LLM backend it's talking to.**

- A `CompanionModelProvider` interface (or equivalent) defines `stream_reply(messages, persona, config) -> AsyncIterator[str]` (exact shape TBD at implementation time) that every backend implements.
- Concrete implementations at launch:
  - **Claude (Anthropic API)** — default for companionship and roleplay modes.
  - **Hosted open-model API** (e.g. OpenRouter or Featherless.ai style provider serving an uncensored/RP-tuned open-weight model) — used for the romantic/sexual/intimate mode, where explicit sexual content is permitted and Claude will refuse.
- **Routing is user-selectable per mode**: each user can choose which backend powers each of their modes (with sane defaults as above), and swap it in settings. The interface is designed so adding a self-hosted vLLM endpoint or a user's own bring-your-own-key/endpoint later is a new implementation of the same interface, not a new code path.
- Self-hosting your own GPU inference was considered and explicitly rejected for v1: a dedicated GPU box runs whether or not it's used (~$700–1500+/mo), and hosted inference APIs bill per token, matching unknown v1 traffic far better. Revisit self-hosting only if usage volume makes the economics flip.

## 3. Modes & Personas

### Modes
1. **Companionship / emotional support** — Claude-backed by default.
2. **Roleplay & interactive fiction** — Claude-backed by default.
3. **Romantic / sexual / intimate** — 18+ gated (see §6). Explicit sexual content is permitted for adult users. Backed by the hosted open-model provider by default, since Claude will not generate this tier of content.

Digital pet mode from `VISION.md` is **not** built in v1 — see §10.

### Personas
- A handful of curated starter personas ship out of the box, roughly one suited to each mode.
- Users can author **fully custom personas**: name, backstory, personality, tone. Saved to the user's account, reusable across sessions.
- **No moderation/screening at persona-creation time.** Users can write whatever they want. Safety is enforced at chat/generation time, not by gatekeeping what personas can be saved (see §5).
- Every persona — starter or custom — is wrapped by a system-level instruction layer that the persona's own text cannot see or override. This layer is where crisis-handling behavior and the hard content exclusion list live. A user cannot write a persona that talks its way out of these rules.

## 4. Conversations & Memory

- **Session model**: multiple separate, named chat sessions per persona (ChatGPT-style), not one unbroken lifelong thread. A user might have a "main" ongoing chat plus separate roleplay-scenario threads with the same companion.
- **Long-term memory** persists and is shared **across all sessions** for a given companion, regardless of which session a fact originated in:
  - Structured facts table: after a session (or periodically during a long one), the LLM extracts discrete facts (name, preferences, ongoing threads/topics) into structured rows.
  - Periodic summarization: session summaries are generated and injected into the system prompt of future sessions, alongside relevant structured facts.
  - Deliberately **not** a raw vector-embedding/RAG store for v1 — structured facts are transparent, editable, and debuggable in a way embeddings aren't.
- **Memory management UI**: users can view every fact the companion has stored about them, edit or delete individual facts, and do a full memory reset. This ships in v1, not deferred — it's both a trust feature and a de facto data-control expectation for a product storing this kind of personal information.

## 5. Safety & Content Policy

### Crisis / distress detection
- On Claude-backed modes: **LLM-judgment based**. The model is instructed to recognize real distress or crisis signals in context and break character — dropping the persona to respond directly and point to real crisis resources (e.g. hotlines) — rather than staying in character. Chosen over a keyword/classifier trigger for its ability to handle nuance and phrasing variety, accepting that it's less mechanically auditable than a rule-based trigger.
- On the hosted open-model (uncensored) backend: that model has **no built-in safety tuning** and cannot be trusted to self-interrupt. This backend gets its own **explicit safety layer**: a keyword/classifier check wrapping every request/response on that backend specifically, independent of persona, that can intercept a conversation and redirect to a safety response even though the underlying model itself won't do this on its own.

### Hard content exclusion list
Enforced at the system/application level, above every persona and every backend, non-negotiable regardless of user request or persona instructions:
- No non-consent themes.
- No minor-coded characters or scenarios, under any framing.
- No real, identifiable people.

This is an application-layer rule (checked/enforced in code and system prompts the persona can't touch), not something delegated to model behavior.

### Content tiers
- Companionship / roleplay modes: whatever Claude will natively produce under normal use — no explicit sexual content.
- Romantic/sexual/intimate mode: explicit sexual content permitted for verified-adult users (see §6), subject to the hard exclusion list above.

## 6. Access Control

- **Auth**: email + password, with Google OAuth as an alternative sign-up/login path.
- **Age gating**: self-attestation only in v1 — a checkbox/DOB entry gates access to the romantic/sexual/intimate mode. No third-party ID verification integration in v1; this is an explicit, flagged gap (see §10), not a permanent design decision.

## 7. Data Handling

- All chat content is **encrypted at rest**.
- Users can **delete individual conversations** at any time.
- Users can optionally enable an **auto-expiry window** (e.g. auto-purge intimate-mode logs after N days) per companion or per mode.
- **No data export feature in v1.** Called out explicitly here as a known gap rather than a silent omission — worth revisiting given the personal nature of the data stored.

## 8. Engagement

- The companion can send **proactive/unprompted messages** (e.g. a check-in after a day of silence, a follow-up on something discussed previously) — but only as an **opt-in feature, off by default**. Users must explicitly enable it per companion in settings.
- Requires a scheduler/background job to evaluate when a proactive message is due; must be paced conservatively to avoid feeling manipulative or spammy — no proactive messages for users who haven't opted in, full stop.

## 9. Cost & Ops

- **No hard per-user usage caps in v1.** Token/inference cost is tracked per user with alerting on unusual spikes; hard caps are revisited if real traffic materializes and costs need bounding.
- Deployment stays a single VPS via Docker Compose until traffic or reliability needs justify moving to managed cloud services.

## 10. Explicitly Out of Scope for v1

Each item below is deferred, not designed against — the architecture should not make these harder to add later than necessary.

| Deferred | Note |
|---|---|
| Digital pet mode | Present in the original vision but cut from v1 scope. If added later, treat as a genuinely separate feature (own data model, stat-decay background job) rather than a persona skin on an existing mode. |
| Voice, avatar/video | Text-only chat interface for v1; provider interface doesn't preclude adding a TTS/avatar layer later. |
| Multiple simultaneous companions per user | Data model shouldn't hard-code a single-companion assumption at the schema level even though the UI only supports one in v1. |
| Payments/subscriptions | No billing in v1; usage tracking (§9) lays groundwork for tiering later if needed. |
| Native mobile apps | Web-only, responsive. API-first backend means a native client can consume the same API later. |
| Multi-language support | English-only; UI strings should still be externalized (not hardcoded inline) so i18n isn't a full rewrite later. |
| Group/multi-user chats | Strictly one user talking to their own companion(s). |
| Third-party ID/age verification | Self-attestation only for now (§6); age-gate check should be an isolated function/service so swapping in a real verification provider later doesn't touch unrelated code. |
