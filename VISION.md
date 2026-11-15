# AI Companion — Product & Business Vision

> **Status**: active direction, last revised 2026-11-16.
> **Document hierarchy**: this file holds the business and product direction — what we're
> building, for whom, and how it makes money. [`SPEC.md`](SPEC.md) is the v1 technical spec.
> [`CLAUDE.md`](CLAUDE.md) is the contributor guide. Where they disagree, the most recent
> dated decision wins, and the loser gets updated rather than left to rot.
>
> **On the numbers**: figures here come from secondary sources (analyst and vendor blogs),
> not primary filings or signed quotes. Anything that would change a real decision is marked
> **[VALIDATE]**. Treat them as the shape of the problem, not as settled facts.

---

## 1. The bet

An AI companion that remembers you, that you can shape, and that can **show you things** —
not just talk.

The product is a multi-mode companion: emotional support, roleplay and interactive fiction,
and a romantic/intimate tier. The wedge is the third mode combined with something the
category leaders structurally cannot ship: **in-chat image and video generation with an
uncensored tier**.

Character.AI and Replika are text-first and heavily filtered. They are backed by investors
and app-store distribution, which means they are permanently constrained — the same
constraints we are choosing to absorb deliberately. Replika's 2023 removal of erotic
roleplay, and the user revolt that followed, is the clearest evidence in the category that
this demand is real, underserved, and punishing to betray.

**Who it's for**: adults who want an ongoing relationship with a character they control,
who have already tried the mainstream apps and hit the filter.

**Why we can win a slice**: we are not trying to beat Character.AI at scale. We are trying
to be the best product for users the incumbents actively refuse to serve, at a price those
users have repeatedly shown they will pay.

## 2. Market reality

The honest version, because the headline numbers are useless:

- 2026 market sizing varies roughly **20×** across sources ($2.9B–$49B) depending entirely
  on what gets counted as an "AI companion". Ignore these. **[VALIDATE]**
- The concrete figure: app-store consumer spend on companion apps was **~$120M in 2025**,
  with revenue per download rising from **$0.52 (2024) to $1.18 (2025)** — the category is
  monetizing better, not just growing. **[VALIDATE]**
- **The top 10% of apps take 89% of category revenue.** This is the number that matters.

That last point sets the quality bar. In a winner-take-most category, a competent but
unremarkable product earns approximately nothing. There is no viable "decent and cheap"
position here. This is why the engineering standards in §7 are a business requirement and
not developer self-indulgence.

**Price anchors** (per month): Character.AI $9.99 · Replika Pro ~$15–20. **[VALIDATE]**

## 3. Strategy: adult-core, decided

The intimate tier is the monetization engine. It is also the single largest source of
existential risk. Both are true, and the strategy is to absorb the risk rather than hedge it.

**Decided 2026-11-16**: adult tier is core to v1, with compliance treated as mandatory
infrastructure. Built as a **bootstrapped solo product**, launching **US-only**.

The alternative — launch safe-for-work, add adult later — trades away the differentiator
precisely when we need it to acquire the first users, and the compliance work still arrives
later with the same bill. Taking it up front means a slower launch and a more defensible one:
every constraint in §4 is a moat against casual competitors, because most will not do it.

What this choice costs is detailed below. It should be re-read before anyone is tempted to
"just use Stripe for now."

## 4. Hard constraints

These are not warnings. Each one dictates architecture or go-to-market.

### 4.1 Payments: ~4–5× the normal cost

Stripe and PayPal prohibit adult AI content. Apple and Google bar it from in-app purchase.

- Billing is **web-only**, through a high-risk processor: CCBill (~10.8–14.5%), Segpay
  (quote-based), Epoch, Verotel. **[VALIDATE — get real quotes]**
- Versus Stripe's ~2.9%, payment processing costs roughly **4–5× more**, and it comes out of
  every subscription forever.
- Expect **rolling reserves** (~5% held for 6 months) — working capital we do not get to use.
- **Chargebacks must stay below ~0.75–1%** or the account is terminated. Not fined: terminated.
- Reportedly **30–50% of merchant applications are rejected on first pass**.

**Design consequences**: chargeback prevention is a first-class product feature, not an
afterthought — clear billing descriptors, obvious cancellation, immediate refunds, email
receipts. A frustrated user who cannot find the cancel button files a chargeback, and enough
of those end the business. Apply for merchant accounts **early**; a 30–50% rejection rate
means this is a lead-time item, not a launch-week task.

### 4.2 Distribution: no app stores

Being barred from in-app purchase effectively means being barred from the stores. So:

- No ASO, no store search, no "featured" placement, no install-button funnel.
- Acquisition is **SEO, content, affiliates, and communities** (Reddit, Discord).
- The web app must feel native on a phone, because the phone browser *is* the app.

**Design consequence**: responsive quality is a growth input, not polish. And SEO means the
marketing site is a real engineering surface, not a landing page.

### 4.3 Age verification: legally required, not a checkbox

`SPEC.md` §6 currently specifies self-attestation. **That is no longer defensible.**

- **26 US states** require real age verification for adult content. **[VALIDATE — the exact
  list changes continuously]**
- Regulators have stated explicitly that a self-declared "I am over 18" tickbox does not
  qualify.
- **Ofcom opened an investigation into Joi.com — an AI companion service — on 15 Jan 2026**,
  over precisely this. A direct competitor is already under investigation for the approach
  our spec currently describes.
- Indicative cost: **~$0.10/check** (age-estimation only) to **~$1.35** (KYC-grade).
  **[VALIDATE]**

**Design consequences**: age verification is a v1 blocker for the intimate tier, and
`SPEC.md` §6 must be amended. Critically — **verify at the point of entering the intimate
tier, not at signup**. Verifying every signup means paying for every tire-kicker; at a 5%
conversion rate that is 20 checks per paying user. Gating at the tier boundary moves the cost
to users who have already shown intent. Keep the check behind one isolated interface so the
vendor can be swapped without touching unrelated code.

### 4.4 California SB 243 applies to us

Effective 1 Jan 2026, binding on any operator serving a user **in California regardless of
where the company is based**. A US launch is in scope. Requirements: **[VALIDATE against the
enacted text]**

- Clear AI disclosure, plus notice that companion chatbots may not suit some minors.
- A **crisis protocol** that refers users to crisis services, uses **evidence-based methods
  for measuring suicidal ideation**, and is **published on the website**.
- For known minors: break reminders every 3 hours, and reasonable measures to prevent
  sexually explicit material.
- Annual reporting to California's Office of Suicide Prevention from 1 July 2027.
- **A private right of action** — individuals can sue directly.

**Design consequence, and it touches code today**:
`backend/src/services/safety/uncensored_guard.py` is, by its own docstring, a keyword
placeholder. SB 243 asks for a documented, evidence-based, published protocol. The gap
between those is a compliance exposure with a private right of action attached. Closing it is
not optional polish — see §9 Phase 3.

The good news: `SPEC.md` §5 already put crisis handling at the application layer, above
persona and provider. The architecture is right; the implementation needs to catch up.

## 5. Unit economics

A model, not a forecast. Every input is an assumption to be replaced with measurement.
Shown at a **$19/mo** intimate tier — above Character.AI, near Replika Pro, justified by
uncensored content plus media generation.

| Line | Per paying user / month | Note |
|---|---|---|
| Revenue | **+$19.00** | |
| Payment processing (~12%) | −$2.28 | Midpoint of CCBill range **[VALIDATE]** |
| Text inference | −$3.06 | See assumptions below |
| Age verification (amortized) | −$0.13 | ~$0.50 once, over ~4-month lifetime |
| Infra (VPS, allocated) | −$0.40 | Single VPS per `SPEC.md` §2 |
| **Gross margin** | **≈ $13.13** | ~69% |

**Inference assumptions**: 60 messages/day; ~3,000 input tokens per turn (system prompt +
persona + injected memory + recent history) and ~250 output; ~$0.50/M input and ~$0.80/M
output for a hosted uncensored open model. That is 1,800 turns → ~5.4M input + 0.45M output
tokens. **[VALIDATE all five]**

### The finding that matters

**Heavy users can be unprofitable.** Holding everything else fixed and scaling only message
volume:

| Volume vs. assumption | Inference | Total cost | Margin |
|---|---|---|---|
| 1× (the model above) | $3.06 | $5.87 | **+$13.13** |
| 3× | $9.18 | $11.98 | +$7.02 |
| 5× | $15.30 | $18.11 | **+$0.89** |
| 6× | $18.36 | $21.16 | **−$2.16** |

Margin is effectively gone by 5× and **inverts at ~6×** — and that is text alone. Media
generation makes it sharper: video is expensive per clip, and a user who discovers it will
use it.

`SPEC.md` §9 currently says **"No hard per-user usage caps in v1,"** with cost tracking and
alerting only. For a venture-funded company that is a reasonable growth stance. **For a
bootstrapped solo operator it is a direct path to negative margin on the most engaged users** —
the exact users who churn hardest when limited.

**Recommendation**: revisit before launch. Fair-use limits generous enough to be invisible to
~95% of users, metered media generation (credits rather than unlimited), and per-user cost
tracking from day one — not after the first surprise invoice.

## 6. What "state of the art UX" means here

Each of these is justified by retention or willingness to pay, not taste.

**Memory that visibly works.** The product promise is being *known*. A companion that forgets
is the category's defining failure. `SPEC.md` §4's structured-facts approach — transparent,
editable, debuggable — is the right call over embeddings, and the memory-management UI is a
trust feature that doubles as a differentiator. Users should be able to *see* what it knows.

**Fast first token.** Streaming is already in place. Latency is felt as personality: a
companion that lags feels like software, which is fatal for the illusion the product sells.

**Persona authoring that is genuinely open.** Per `SPEC.md` §3, no screening at creation
time; safety is enforced at generation time. Users who invest in authoring a character have
switching costs — that is the retention moat.

**Multimodal, inline.** Already built: the companion can send images and video within the
conversation, and the backend infers intent from the message rather than requiring buttons.
This is the single clearest "we have something they don't" feature. It needs metering (§5),
not restraint.

**Phone-native on the web.** The browser is the only distribution channel (§4.2). Anything
that feels like a desktop site shrunk down loses.

**Deliberately deferred**: voice. It is the obvious next frontier and the obvious next
pricing tier, but it multiplies cost and latency, and the product has no paying users yet.

## 7. Engineering standards as a business asset

In a market where the top decile takes 89% of revenue, quality is commercial strategy. Three
things specifically earn their keep:

**The provider seam is existential.** `services/providers/base.py` defines
`CompanionModelProvider.stream_reply(...)`, and nothing outside the provider layer knows
which backend serves a request. That is not architectural neatness — uncensored model hosting
is a *supply risk* (§10). When a provider changes policy, the ability to swap vendors by
adding one class instead of rewriting the app is the difference between an afternoon and an
outage. The same pattern already generalized cleanly to images (`image_router.py`) and video
(`video_router.py`), which is evidence it is the right seam.

**Safety at the application layer, above persona and provider.** `uncensored_guard.py`,
`image_content_guard.py` and `video_content_guard.py` enforce rules that no persona text can
argue its way out of. §4.4 makes this a legal requirement, not just an ethical one.

**Tests that permit fast change.** 134 tests today. For a solo operator with no QA, the suite
*is* the ability to ship on a weekend without fear.

**The standard**: Pydantic v2 contracts across boundaries, full type annotations,
Google-style docstrings, fail-fast config. Already in force; see `CLAUDE.md`.

## 8. Monetization design

| Tier | Price | Includes |
|---|---|---|
| Free | $0 | Companionship + roleplay, capped daily messages, no memory persistence beyond a short window, no media generation |
| Companion | ~$9/mo | Unlimited text, full persistent memory, persona authoring, image generation (metered) |
| Intimate | ~$19/mo | Everything above, plus the uncensored tier and video generation (metered). Requires age verification (§4.3) |

**Reasoning**: the free tier must demonstrate memory — the core promise — but not retain it,
because persistence is the thing worth paying for. Image generation sits in the mid tier as
the visible upgrade trigger. Age verification gates only the top tier, keeping §4.3's cost on
users with demonstrated intent.

**Annual billing matters more than usual here**: it cuts payment-processing touchpoints and
chargeback exposure (§4.1), and improves the cash position a bootstrapped operator actually
runs on. **[VALIDATE pricing against willingness-to-pay — these are anchored to competitors,
not researched.]**

## 9. Path to first revenue

**Where we actually are.** The repository is a walking skeleton with an unusually rich media
stack bolted on:

- ✅ Streaming chat, multi-provider routing (Claude, OpenRouter, OpenAI, Ollama)
- ✅ Image generation (3 providers) and video generation (2 providers), intent detection,
  content guards, per-modality model pickers
- ❌ **No database. No authentication. No persistence. One hardcoded persona.**

Nothing a business requires exists yet. The media differentiator is built; the product is not.

| Phase | Goal | Contents |
|---|---|---|
| **1. Foundation** | A user can come back | Postgres, accounts (email + Google OAuth), persisted sessions |
| **2. The promise** | It remembers you | Structured-facts memory across sessions, memory-management UI, starter + custom personas |
| **3. Legal to operate** | Can serve the intimate tier | Age verification at tier boundary, SB 243 crisis protocol (evidence-based, published), AI + suitability disclosures |
| **4. Able to take money** | First paying user | High-risk merchant account (**apply during Phase 1** — 30–50% first-pass rejection), subscription billing, usage metering, cancellation flow built for chargeback avoidance |
| **5. Findable** | Users arrive | SEO-oriented marketing site, content, community presence |

Phases 3 and 4 have long external lead times — verification vendors and merchant
underwriting — so start both earlier than their position implies.

## 10. Risks and kill criteria

| Risk | Why it's real | Trigger to act |
|---|---|---|
| **Processor termination** | Chargebacks >1% ends billing entirely (§4.1) | Chargeback ratio >0.5%: stop feature work, fix billing UX |
| **Model supply** | Uncensored hosting is a vendor policy away from vanishing | Any provider policy change: exercise the §7 seam, keep a second vendor warm |
| **Heavy-user margin** | Top users can cost more than they pay (§5) | Any user >3× median inference cost: ship metering |
| **Regulatory escalation** | SB 243 carries a private right of action; state laws are multiplying | New state law in a served market: geo-gate rather than ignore |
| **Trust betrayal** | Replika's ERP removal destroyed user trust overnight | Never reduce intimate-tier capability for existing paying users without migration and notice |
| **Solo-operator capacity** | Compliance + product + growth is a lot for one person | If Phase 3 slips twice, cut scope rather than quality |

**Kill criterion**: if no high-risk merchant account can be secured after three serious
applications, the adult-core strategy is not executable as a solo bootstrap. Revisit §3 —
SFW-first is the fallback, not a failure.

## 11. Out of scope

Deferred, not designed against. The architecture should not make these harder than necessary.

- Digital pet mode — a separate feature if ever, not a persona skin
- **Voice** — the next tier, after paying users exist (§6)
- Multiple simultaneous companions — but don't hard-code single-companion assumptions in the schema
- Native mobile apps — barred by §4.2 regardless
- Multi-language — externalize UI strings anyway
- Group/multi-user chats
- Non-US markets — the UK/EU regime (§4.3) is a deliberate later decision, not an oversight
