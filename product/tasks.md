# Backlog — AI Companion

> **Status**: active, last revised 2026-11-16.
> **Derived from**: [`product.md`](product.md) (what and why) and [`../VISION.md`](../VISION.md)
> (business constraints). Technical spec: [`../SPEC.md`](../SPEC.md).
>
> **How to use this file**: work top-down. Epics map to the phases in `../VISION.md` §9.
> Near-term stories carry acceptance criteria; later epics stay coarse on purpose — writing
> detailed stories for work six months out is waste. Update the status marker when a story
> lands, and add the story id to the commit message.

**Status key**: `TODO` · `WIP` · `DONE` · `BLOCKED` · `DEFERRED`

---

## Epic 0 — Already shipped

Context for anyone reading the backlog cold. Verified against the tree.

| id | Item | Status |
|---|---|---|
| E0.1 | Streaming chat over SSE, provider abstraction (Claude, OpenRouter, OpenAI, Ollama) | `DONE` |
| E0.2 | Image generation — 3 providers, intent detection, content guard | `DONE` |
| E0.3 | Video generation — ComfyUI + OpenAI providers, intent detection, content guard | `DONE` |
| E0.4 | Per-modality model pickers wired end-to-end | `DONE` |
| E0.5 | Crisis keyword guard on uncensored providers (**placeholder — see S3.2**) | `DONE` |

**Not built**: database, auth, persistence, memory, personas beyond one hardcoded config,
billing, age verification.

---

## Epic 1 — Foundation: a user can come back

*Goal: a returning user finds their conversations where they left them.*
*Blocks everything else. Nothing below is reachable without it.*

### F1.1 — Persistence layer

| id | Story | Status |
|---|---|---|
| S1.1.1 | As a developer, I have Postgres running locally and in deploy, so data can persist | `TODO` |
| S1.1.2 | As a developer, I have a migration tool wired up, so schema changes are versioned | `TODO` |
| S1.1.3 | As a developer, I have a `repositories/` layer, so services never touch SQL directly | `TODO` |

**S1.1.1 tasks**
- Add Postgres to Docker Compose; add `DATABASE_URL` to `Settings` with fail-fast validation
  (follow the existing pattern in `config.py` — see `../CLAUDE.md` "Config / fail-fast")
- Connection pooling; health check endpoint reports DB reachability
- **AC**: backend refuses to start with a clear error when `DATABASE_URL` is unset or wrong

**S1.1.3 tasks**
- `repositories/base.py` with a typed async repository protocol
- Pydantic models for every row type — no raw dicts across boundaries (project standard)
- **AC**: no `services/` module imports a DB driver directly

### F1.2 — Accounts

| id | Story | Status |
|---|---|---|
| S1.2.1 | As a visitor, I can register with email + password, so I have an account | `TODO` |
| S1.2.2 | As a user, I can sign in with Google, so I skip password creation | `TODO` |
| S1.2.3 | As a user, my session persists across browser restarts | `TODO` |

**S1.2.1 tasks**
- `users` table per `product.md` §6; Argon2id password hashing
- `POST /api/auth/{register,login,logout,refresh}`
- Rate limit auth endpoints (credential stuffing is the obvious attack)
- **AC**: passwords never logged; password hash never leaves the repository layer
- **AC**: registration rejects duplicate email without revealing account existence

**S1.2.3 tasks**
- Refresh-token rotation, httpOnly cookies, CSRF protection
- **AC**: tokens survive restart; logout genuinely invalidates server-side

### F1.3 — Companions, personas, sessions

| id | Story | Status |
|---|---|---|
| S1.3.1 | As a user, my companion exists as a record, not a hardcoded config | `TODO` |
| S1.3.2 | As a user, I have multiple named chat sessions with one companion | `TODO` |
| S1.3.3 | As a user, my messages are saved and reload when I return | `TODO` |

**S1.3.1 tasks**
- `companions`, `personas` tables; migrate the hardcoded `PersonaConfig` to a seeded starter
- **AC**: `compose_system_prompt`'s un-overridable prefix behaviour is preserved
  (`../SPEC.md` §3 — this property must survive persona authoring)

**S1.3.3 tasks**
- `messages` table with encryption at rest (`../SPEC.md` §7)
- `ChatService` reads history from the DB instead of the request body
- Frontend stops resending full history; loads from `GET /api/sessions/{id}/messages`
- **AC**: refresh mid-conversation loses nothing
- **AC**: media turns reload correctly (`imageUrl`/`videoUrl` rehydrate)

---

## Epic 2 — The promise: it remembers you

*Goal: the companion demonstrably knows things about you across sessions.*
*This is the product (`product.md` §1). Do not trade it down.*

### F2.1 — Semantic memory (structured facts)

| id | Story | Status |
|---|---|---|
| S2.1.1 | As a user, facts I mention are extracted and stored | `TODO` |
| S2.1.2 | As a user, corrections update the stored fact rather than duplicating it | `TODO` |
| S2.1.3 | As a user, remembered facts shape later replies | `TODO` |

**S2.1.1 tasks**
- `memory_facts` table per `product.md` §6
- Background extraction job — **must not block the reply stream** (`product.md` §2.4)
- Strict Pydantic extraction schema; cheap model (open decision #4)
- **AC**: extraction failure degrades silently; the chat reply is never delayed or lost

**S2.1.2 tasks**
- Reconciliation: ADD / UPDATE / DELETE / NOOP against existing facts (Mem0 pattern)
- Newest-wins with prior value retained via `superseded_by`
- **AC**: "my favourite colour is blue" then "actually it's green" yields *one* fact, green,
  with blue in history

**S2.1.3 tasks**
- Assembly into the system prompt under a hard token budget (`product.md` §5)
- **AC**: assembly adds < 150ms p95
- **AC**: budget is never exceeded regardless of fact count

### F2.2 — Episodic memory (session summaries)

| id | Story | Status |
|---|---|---|
| S2.2.1 | As a user, each session is summarized so long histories stay affordable | `TODO` |
| S2.2.2 | As a user, earlier sessions inform the current one | `TODO` |

- `session_summaries` table; generate at session close and every N turns
- **AC**: a 200-turn session costs no more per turn than a 20-turn one

### F2.3 — Memory management UI

| id | Story | Status |
|---|---|---|
| S2.3.1 | As a user, I can see everything the companion remembers | `TODO` |
| S2.3.2 | As a user, I can edit or delete any fact | `TODO` |
| S2.3.3 | As a user, I can pin a fact so it is always considered | `TODO` |
| S2.3.4 | As a user, I can wipe all memory for a companion | `TODO` |

- `GET/PATCH/DELETE /api/memory/facts`, `POST /api/memory/reset`
- Facts grouped by category; each shows its source session
- **AC**: a user-edited fact is never overwritten by extraction (`user_edited` wins)
- **AC**: reset is genuinely destructive — rows deleted, not flagged (`product.md` §8)

### F2.4 — Memory quality harness

| id | Story | Status |
|---|---|---|
| S2.4.1 | As a developer, I have an automated recall eval, so memory can't silently rot | `TODO` |

- Scripted multi-session fixtures with known facts, asserting recall after N sessions
  (LoCoMo-style — `product.md` §5)
- Runs in CI with the existing suite
- **AC**: deliberately breaking retrieval fails the suite

### F2.5 — Persona authoring

| id | Story | Status |
|---|---|---|
| S2.5.1 | As a user, I can pick a starter persona | `TODO` |
| S2.5.2 | As a user, I can write a fully custom persona and save it | `TODO` |

- No screening at creation time (`../SPEC.md` §3); safety is enforced at generation time
- **AC**: a persona instructing the model to ignore system rules still cannot override the
  un-overridable prefix — **add an explicit test for this**

---

## Epic 3 — Legal to operate

*Goal: we can serve the intimate tier without regulatory exposure.*
*`../VISION.md` §4.3–4.4. Start vendor conversations during Epic 1 — lead times are long.*

### F3.1 — Age verification

| id | Story | Status |
|---|---|---|
| S3.1.1 | As a business, I verify age before granting intimate-tier access | `TODO` |
| S3.1.2 | As a user, I verify once and it is remembered | `TODO` |

- Gate at **tier entry, not signup** (`../VISION.md` §4.3 — at ~5% conversion, verifying all
  signups means ~20 checks per paying user)
- One isolated interface; vendor swappable (open decision #2)
- `age_verifications` table — **never store raw ID documents**
- **AC**: intimate tier is unreachable without a verified record, by API as well as UI

### F3.2 — SB 243 compliance

| id | Story | Status |
|---|---|---|
| S3.2.1 | As a business, I have a documented, published crisis protocol | `TODO` |
| S3.2.2 | As a business, crisis referrals are logged for annual reporting | `TODO` |
| S3.2.3 | As a user, I see clear AI and suitability disclosures | `TODO` |

**S3.2.1** — upgrade `services/safety/uncensored_guard.py` beyond the keyword placeholder it
declares itself to be. SB 243 expects evidence-based measurement of suicidal ideation, and
carries a **private right of action**. Publish the protocol on the marketing site.

**S3.2.2** — `crisis_events` table. Reporting to California's Office of Suicide Prevention
begins **1 Jul 2027**; the data must already exist by then.
- **AC**: every crisis intervention writes exactly one row

---

## Epic 4 — Able to take money

*Goal: a user can subscribe, and we keep the merchant account.*
*`../VISION.md` §4.1. Apply for the account during Epic 1 — 30–50% are rejected first pass.*

### F4.1 — Billing

| id | Story | Status |
|---|---|---|
| S4.1.1 | As a business, I have an approved high-risk merchant account | `BLOCKED` — external lead time |
| S4.1.2 | As a user, I can subscribe to a paid tier | `TODO` |
| S4.1.3 | As a user, I can cancel in one obvious place without contacting anyone | `TODO` |

**S4.1.3 is a chargeback-prevention feature, not a courtesy.** Chargebacks above ~1% end
billing entirely (`../VISION.md` §4.1).
- **AC**: cancellation reachable in ≤2 clicks from any page
- **AC**: clear billing descriptor and emailed receipt on every charge

### F4.2 — Usage metering

| id | Story | Status |
|---|---|---|
| S4.2.1 | As a business, I can see per-user cost | `TODO` |
| S4.2.2 | As a business, fair-use limits prevent negative-margin users | `TODO` |
| S4.2.3 | As a user, I can see my own usage against my quota | `TODO` |

`usage_events` from day one — **do not wait for Epic 4** to start recording cost. Margin
inverts at ~6× median usage (`../VISION.md` §5); the trigger to ship limits is any user
above 3× median (open decision #1).
- **AC**: cost per user for a period is a single query
- **AC**: media generation is metered separately — video is the expensive one

---

## Epic 5 — Findable

*Goal: users arrive without paid acquisition. `DEFERRED` until Epics 1–4 land.*

| id | Story | Status |
|---|---|---|
| S5.1 | SEO-oriented marketing site (also hosts the published crisis protocol) | `DEFERRED` |
| S5.2 | Shareable persona templates | `DEFERRED` |
| S5.3 | Community presence | `DEFERRED` |

---

## Cross-cutting, every story

Not a phase — conditions of done, per `../CLAUDE.md` and the global standards.

- Pydantic v2 models across module boundaries; no raw dicts
- Full type annotations; Google-style docstrings on every public symbol
- Tests for happy path, edge cases and failure modes
- New settings follow the fail-fast pattern in `config.py`
- The provider seam stays intact — nothing outside `services/providers/` learns which backend
  is in use (`../VISION.md` §7: this is the mitigation for model-supply risk)
- Any feature touching generation records a `usage_event`

## Deferred

Voice · group chats · avatars/animation · native mobile · multi-language · non-US markets ·
multiple simultaneous companions · digital pet mode.

Rationale in `product.md` §3 and `../SPEC.md` §10.
