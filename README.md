# AI Companion

A multi-mode AI companion: emotional support, roleplay and interactive fiction, and a
romantic/intimate tier. Text chat with **in-conversation image and video generation**.

**Current state**: a walking skeleton with an unusually complete media stack. Streaming chat
across four LLM providers, image generation (3 backends) and video generation (2 backends)
all work. There is **no database, no authentication, no persistence, and one hardcoded
persona** — see [`product/tasks.md`](product/tasks.md) Epic 0 for exactly what exists.

```bash
./dev.sh                                  # both servers, with setup checks
python3 scripts/tasks.py install-hooks    # once per clone — enables the commit-msg hook
python3 scripts/tasks.py next             # what to work on
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

1. **Start in [`product/tasks.md`](product/tasks.md)** — `python3 scripts/tasks.py next`.
   If there's no story for the work, add one before writing code; work that isn't in the
   backlog isn't prioritised against anything.
2. **Check [`product/product.md`](product/product.md)** for the design and acceptance
   criteria, and [`VISION.md`](VISION.md) if the work affects cost, compliance or pricing.
3. **Follow [`CLAUDE.md`](CLAUDE.md)** — Pydantic v2 across boundaries, full type
   annotations, Google-style docstrings, tests for happy path and failure modes.
4. **Update the story status** with `python3 scripts/tasks.py set <id> DONE`, and reference
   the id in the commit message — the `commit-msg` hook enforces the latter.
5. **If the work contradicts a document, change the document.** A spec that disagrees with
   the code is worse than no spec.

### Backlog tooling

Nothing updates the backlog by itself. These make it cheap to keep honest:

| Command | Does |
|---|---|
| `tasks.py next` | Next actionable story |
| `tasks.py list --status TODO --epic 1` | Filtered view |
| `tasks.py set S1.1.1 DONE` | Change status (rewrites one line) |
| `tasks.py check` | Validate ids, statuses and doc links |
| `tasks.py install-hooks` | Enable the git hooks (`dev.sh` does this for you) |

**Status mostly maintains itself.** The `post-commit` hook reads the commit message and:

- moves a referenced story `TODO` → `WIP` — committing against a story means work started
- moves it to `DONE` only when you say so explicitly: `closes S1.1.1`, `fixes S1.1.1`

`BLOCKED` and `DEFERRED` are never touched — those are deliberate, not stale. The updated
`tasks.md` is **staged, not amended**, so it rides along with your next commit; amending from
a hook rewrites history and breaks rebases.

The flip side: mentioning a story id in an unrelated commit will advance it. Use a
`docs:`/`chore:` prefix or `[no-story]` when you are not actually working on it.

`DONE` is the one thing left to you, deliberately — no tool can know you consider work
finished, and a false `DONE` is worse than a stale `TODO`.

`backend/tests/unit/test_backlog.py` runs the same validations in the normal suite, so a
broken table or a renamed document fails CI rather than rotting quietly.

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
