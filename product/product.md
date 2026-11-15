# Product Definition — AI Companion

> **Status**: active, last revised 2026-11-16.
> **Reads from**: [`../VISION.md`](../VISION.md) — why we're building this and the business
> constraints. **Feeds**: [`tasks.md`](tasks.md) — the backlog derived from this document.
> **Technical spec of record**: [`../SPEC.md`](../SPEC.md). **Contributor guide**:
> [`../CLAUDE.md`](../CLAUDE.md).
>
> This turns the business vision into something buildable: what we ship, in what order, and
> the technical design behind it. Market claims come from secondary research and are marked
> **[VALIDATE]** wherever a real decision depends on them.

---

## 1. The product thesis

**Memory is the product. Media is the wedge.**

Feature research across the category converges on one finding: *persistent memory is what
users value most* — ranked consistently above avatars, voice, or images. **[VALIDATE — this
comes from review-site aggregation, not an independent study.]** A companion that forgets is
a generic chatbot, and that is the category's defining failure.

The competitive gap is specific:

| Product | Memory | Media generation |
|---|---|---|
| Character.AI | Weak — forgets between sessions; added Story Memory/Facts May 2026 | None |
| Nomi | **Strong** — three time scales, editable "Mind Map" | Limited |
| Kindroid | **Strong** — editable memory dashboard | Limited |
| Candy AI | **Weak** — session-level only | **Strong** — visuals-first |
| JanitorAI | Weak — throttled free model | None |

**[VALIDATE — compiled from 2026 review blogs that disagree with one another.]**

Nobody does **both** well. Candy AI has the visuals but forgets you; Nomi and Kindroid
remember you but generate little. We already own the media half (3 image providers, 2 video
providers, inline intent detection). The bet is to pair it with best-in-class memory.

That ordering drives the backlog: **memory is Phase 2 and is not deferrable.** The media
stack is a differentiator we happen to already have — it is not a substitute for the thing
users actually pay for.

## 2. Product principles

1. **Never silently forget.** If the companion can't recall something, that is a visible,
   explainable state — not a mystery. Memory is inspectable by design.
2. **The user owns the character.** Open persona authoring, no screening at creation time.
   Safety is enforced at generation time (`../SPEC.md` §3, §5).
3. **The user owns the data.** View, edit, delete any remembered fact; full reset; delete
   conversations. A trust feature and a legal expectation at once.
4. **Latency is personality.** A laggy companion feels like software, which kills the
   illusion the product sells.
5. **Every feature has a unit cost.** `../VISION.md` §5 shows margin inverting at ~6× median
   usage. Nothing ships without knowing its per-user cost.
6. **Compliance is a feature, not a tax.** Age verification and crisis handling are surfaces
   users touch. Design them; don't bolt them on.

## 3. Feature set

Ordered by the phases in `../VISION.md` §9. Each feature carries its reason.

### Phase 1 — Foundation: *a user can come back*

| Feature | Why |
|---|---|
| Accounts (email+password, Google OAuth) | Memory needs somewhere to attach |
| Persisted conversations | Today the client resends everything; nothing survives a refresh |
| Multiple named sessions per companion | `../SPEC.md` §4 — a "main" thread plus scenario threads |
| Companion + persona data model | Replaces today's single hardcoded persona |

### Phase 2 — The promise: *it remembers you*

| Feature | Why |
|---|---|
| **Three-tier memory** (working / episodic / semantic) | The core differentiator — §5 |
| **Memory management UI** | Nomi and Kindroid both expose editable memory; table stakes at the top of this market, and a trust feature |
| Persona authoring (starter + custom) | Switching cost — a user who authored a character doesn't leave |
| Memory-aware prompt assembly | Facts and summaries injected under a token budget |

### Phase 3 — Legal to operate: *can serve the intimate tier*

| Feature | Why |
|---|---|
| Age verification at the tier boundary | `../VISION.md` §4.3 — legally required; gating at the boundary avoids paying for tire-kickers |
| SB 243 crisis protocol (evidence-based, published) | `../VISION.md` §4.4 — carries a private right of action |
| AI + suitability disclosures | SB 243; also `../SPEC.md` §1 |
| Crisis event logging | SB 243 requires annual reporting from 1 Jul 2027 — the data must already exist |

### Phase 4 — Able to take money

| Feature | Why |
|---|---|
| Subscription billing (high-risk processor) | `../VISION.md` §4.1 |
| **Usage metering + fair-use limits** | `../VISION.md` §5 — margin inverts at ~6× median usage |
| Self-serve cancellation | Chargebacks >1% terminate the merchant account. An un-cancellable subscription *is* a chargeback |
| Billing transparency (descriptors, receipts) | Same reason |

### Phase 5 — Findable

| Feature | Why |
|---|---|
| Marketing site, SEO surface | No app stores (`../VISION.md` §4.2) — organic is the only channel |
| Shareable persona templates | Community-driven acquisition |

### Explicitly deferred

Voice (next tier, once paying users exist), group chats, avatars/animation, native mobile
(barred anyway), multi-language, non-US markets.

## 4. System architecture

Current state, verified against the tree: FastAPI backend with a clean provider seam,
React/TS frontend, **no database, no auth, no persistence, one hardcoded persona**. Media
generation is fully built.

```
React/TS SPA ──SSE──> FastAPI
                        ├── api/routes/        chat, models, (new) auth, memory, billing
                        ├── services/
                        │    ├── providers/        text LLMs  (Claude, OpenRouter, …)
                        │    ├── image_providers/  image generation
                        │    ├── video_providers/  video generation
                        │    ├── memory/           (new) extraction, retrieval, assembly
                        │    ├── safety/           crisis + media content guards
                        │    └── billing/          (new) processor webhooks, metering
                        └── repositories/      (new) Postgres data access
                                                  │
                                          Postgres (encrypted at rest)
```

**What stays**: the provider abstraction (`services/providers/base.py`) is the load-bearing
seam and must not be weakened — `../VISION.md` §10 names model supply as an existential risk,
and cheap vendor-swapping is the mitigation.

**What's new**: a `repositories/` layer (per the project structure in `../CLAUDE.md`), a
`memory/` service, and `billing/`. `ChatService` gains memory assembly before provider
dispatch and fact extraction after.

## 5. Memory subsystem — the core design

The feature most worth getting right. Informed by published work: **Mem0** (LLM-driven fact
extraction with ADD/UPDATE/DELETE/NOOP reconciliation), **MemoryBank** (built for a companion
chatbot; timestamped sessions distilled into event summaries plus a global user profile), and
the short/mid/long-term hierarchy common to both. **[VALIDATE — arXiv preprints, not settled
practice.]**

`../SPEC.md` §4 already chose structured facts + periodic summarization over vector/RAG. The
research supports that: Mem0 argues for capturing salient facts rather than retrieving large
chunks of original text. We keep it and add the time-scale hierarchy that Nomi exposes as its
differentiator.

### Three tiers

| Tier | Holds | Lifetime | Source |
|---|---|---|---|
| **Working** | Last N turns verbatim | Current session | The messages table |
| **Episodic** | Per-session summaries, timestamped | Permanent | Generated at session close / every N turns |
| **Semantic** | Discrete structured facts | Permanent, user-editable | Extracted asynchronously post-turn |

### Fact extraction

Runs **asynchronously after the reply is streamed** — never in the request path, because
latency is personality (§2.4).

1. Post-turn, a background job sends the exchange to a cheap model with a strict extraction
   schema (Pydantic, per project standards).
2. Each candidate is reconciled against existing facts for that companion: **ADD** (new),
   **UPDATE** (changed), **DELETE** (contradicted), **NOOP** (already known).
3. Conflicts resolve newest-wins, but the prior value is retained so the UI can show
   *"changed from X on \<date\>"*.
4. Facts are **scoped to the companion** and shared across all its sessions (`../SPEC.md` §4).

### Retrieval and assembly

Per turn, under an explicit **token budget** — a hard cost control (§2.5):

```
system prompt = persona system text (un-overridable prefix, ../SPEC.md §3)
              + global profile summary
              + top-K relevant semantic facts
              + most recent episodic summaries
              + working memory (last N turns verbatim)
```

Relevance in v1 is recency + access frequency + explicit pinning — **not** embeddings. If that
proves insufficient, vector search over facts is the first upgrade, and the fact schema must
not preclude it.

### Memory UI

Non-negotiable, and a differentiator. Users can browse facts by category, edit a value
inline, delete a fact, pin one as always-injected, see which session it came from, and
perform a full reset.

### How we know it works

Memory quality needs a test, not vibes. Build a small eval harness in the spirit of
**LoCoMo** (a published long-term conversational memory benchmark): scripted multi-session
conversations with known facts, asserting recall after N sessions, running in CI alongside
the existing 134 tests. **A memory feature with no regression test will silently rot.**

## 6. Data model

Postgres. All chat content encrypted at rest (`../SPEC.md` §7).

| Table | Key columns | Notes |
|---|---|---|
| `users` | email, password_hash, google_sub, tier, created_at | |
| `age_verifications` | user_id, vendor, vendor_ref, method, result, verified_at | Never store raw ID documents |
| `companions` | user_id, name, persona_id, mode | One per user in v1; schema allows many |
| `personas` | user_id (null = starter), name, backstory, personality, tone, system_text | |
| `sessions` | companion_id, title, last_message_at | Multiple named sessions |
| `messages` | session_id, role, content, media_url, media_type, token_count | Content encrypted |
| `memory_facts` | companion_id, category, key, value, confidence, source_message_id, pinned, user_edited, superseded_by | The semantic tier |
| `session_summaries` | session_id, companion_id, summary, covers_from, covers_to | The episodic tier |
| `usage_events` | user_id, kind (text/image/video), model_id, tokens_in, tokens_out, cost_cents | Powers metering + margin monitoring |
| `subscriptions` | user_id, processor, processor_sub_id, tier, status, period_end | |
| `crisis_events` | user_id, session_id, trigger, action_taken, created_at | **SB 243 annual reporting from 1 Jul 2027** |

`crisis_events` is easy to overlook and legally required — the data must be accumulating
*before* the first report is due.

## 7. API surface (additions)

Existing: `POST /api/chat/stream`, `GET /api/models{,/images,/videos}`.

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/{register,login,logout,refresh}` | Accounts |
| `GET /api/auth/google/{start,callback}` | OAuth |
| `GET/POST/PATCH/DELETE /api/companions`, `/personas` | Companion + persona CRUD |
| `GET/POST/DELETE /api/sessions`, `/sessions/{id}/messages` | Conversation history |
| `GET/PATCH/DELETE /api/memory/facts`, `POST /api/memory/reset` | Memory management UI |
| `POST /api/age-verification/{start,callback}` | Tier-boundary gate |
| `GET /api/billing/subscription`, `POST /api/billing/cancel` | Self-serve cancellation |
| `POST /api/webhooks/{processor}` | Subscription lifecycle |
| `GET /api/usage` | User-visible quota |

## 8. Non-functional requirements

| Area | Requirement | Why |
|---|---|---|
| **Latency** | First token < 1s p95; memory assembly < 150ms | §2.4 |
| **Memory cost** | Hard token budget per turn, enforced in code | Margin inverts at ~6× usage |
| **Cost observability** | Per-user cost queryable from day one | `../VISION.md` §10 trigger: any user >3× median |
| **Availability** | Single VPS, graceful provider failover | A provider outage is not a product outage |
| **Security** | Chat encrypted at rest; no raw ID docs; secrets never in the repo | `../SPEC.md` §7 |
| **Privacy** | Deletion is genuinely destructive; memory reset means reset | Trust is the product |
| **Compliance** | Crisis protocol published; disclosures visible; crisis events logged | SB 243, private right of action |
| **Testing** | Every feature carries tests; memory has a recall eval | Solo operator, no QA |

## 9. Open decisions

Each blocks the phase named.

1. **Fair-use limits** — `../SPEC.md` §9 says no caps; `../VISION.md` §5 says margin inverts
   at ~6×. *Blocks Phase 4. Recommendation: limits generous enough to be invisible to ~95% of
   users, plus metered media credits.*
2. **Age verification vendor** — quote-based (~$0.10–$1.35/check). *Blocks Phase 3. Get three
   quotes; keep behind one interface.*
3. **Payment processor** — 30–50% first-pass rejection; apply during Phase 1.
4. **Extraction model** — which cheap model runs fact extraction, and its per-turn cost.
5. **Media quota design** — credits vs rate limits. Video is the expensive one.
