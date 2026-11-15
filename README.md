# AI Companion

A multi-mode AI companion: emotional support, roleplay and interactive fiction, and a
romantic/intimate tier. Text chat with **in-conversation image and video generation**.

**Current state**: a walking skeleton with an unusually complete media stack. Streaming chat
across four LLM providers, image generation (3 backends) and video generation (2 backends)
all work. There is **no database, no authentication, no persistence, and one hardcoded
persona** — see [`product/tasks.md`](product/tasks.md) Epic 0 for exactly what exists.

```bash
./dev.sh          # both servers, with setup checks
```

Full setup, including optional local video generation, is in [`USAGE.md`](USAGE.md).

## Documentation map

**Read these before starting any task.** Each answers a different question, and they are
ordered from why to how:

| Document | Answers | Read it when |
|---|---|---|
| [`VISION.md`](VISION.md) | *Why* — market, monetization, unit economics, regulatory constraints | Deciding whether something is worth building |
| [`product/product.md`](product/product.md) | *What* — feature set, memory design, data model, API surface, NFRs | Designing a feature |
| [`product/tasks.md`](product/tasks.md) | *When* — epics → stories → tasks with acceptance criteria | Picking up work |
| [`SPEC.md`](SPEC.md) | *Rules* — authoritative v1 technical spec: personas, memory, safety, access control | Touching any of those areas |
| [`CLAUDE.md`](CLAUDE.md) | *How* — architecture, conventions, the load-bearing seams | Writing code |
| [`USAGE.md`](USAGE.md) | *Run it* — setup, commands, troubleshooting | Something won't start |

Where documents disagree, **the most recent dated decision wins**, and the losing document
gets updated in the same change rather than left to rot.

## Working agreement

Every task:

1. **Start in [`product/tasks.md`](product/tasks.md).** Find the story. If there isn't one,
   add it before writing code — work that isn't in the backlog isn't prioritised against
   anything.
2. **Check [`product/product.md`](product/product.md)** for the design and acceptance
   criteria, and [`VISION.md`](VISION.md) if the work affects cost, compliance or pricing.
3. **Follow [`CLAUDE.md`](CLAUDE.md)** — Pydantic v2 across boundaries, full type
   annotations, Google-style docstrings, tests for happy path and failure modes.
4. **Update the story status** and reference its id in the commit message.
5. **If the work contradicts a document, change the document.** A spec that disagrees with
   the code is worse than no spec.

### Three constraints that are easy to break by accident

- **The provider seam.** Nothing outside `backend/src/services/providers/` may know which
  LLM backend serves a request. Uncensored model hosting is a supply risk; cheap vendor
  swapping is the mitigation (`VISION.md` §7, §10).
- **The un-overridable system prefix.** A persona's own text must never be able to talk its
  way past the safety layer (`SPEC.md` §3, §5).
- **Per-user cost.** Margin inverts at roughly 6× median usage (`VISION.md` §5). Anything
  that generates should record a `usage_event`.

## Layout

```
backend/     FastAPI — providers, safety guards, chat orchestration
frontend/    React + TypeScript SPA
product/     Product definition and backlog
```

## Tests

```bash
cd backend && source .venv/bin/activate && pytest   # 134 tests
cd frontend && npm run build                        # tsc type-check + build
```

There is no frontend test suite yet; `npm run build` type-checks it.
