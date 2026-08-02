# AI Companion — Vision

> Resolved into a full spec in `SPEC.md` — this file is kept as the original rough intent; see SPEC.md for the authoritative v1 decisions.

## Core value prop
- Multi-mode companion app: emotional support/companionship, roleplay & interactive fiction, and a romantic/sexual/intimate companion experience
- Digital pet mode was considered but cut from v1 scope (see SPEC.md §10)
- Users pick a mode and either a starter persona or a fully custom one they author themselves

## Modality (v1)
- Text chat, for now. Voice/avatar are later, not v1.

## Rough scope (v1)
- One companion per user to start, chosen from a few starter personas or a fully custom one the user writes and saves
- Memory that persists across sessions — remembers key facts and ongoing threads, not just within one chat — with a UI to view/edit/delete what's remembered
- Basic accounts (email/password + Google OAuth), so memory has somewhere to attach

## Hard constraints
- LLM API: Anthropic Claude as the default backend for companionship/roleplay; a hosted open-model API (e.g. OpenRouter/Featherless-style) for the romantic/sexual/intimate mode, since Claude won't generate explicit content. Provider choice is abstracted and user-selectable per mode — see SPEC.md §2.
- Framework/stack: Python + FastAPI backend, React + TypeScript frontend, Postgres, deployed on a single VPS via Docker Compose — see SPEC.md §2.

## Explicitly out of scope for v1
- Digital pet mode
- Voice, avatar/video
- Multiple simultaneous companions per user
- Payments/subscriptions
- Native mobile apps
- Multi-language support
- Group/multi-user chats
- Third-party ID/age verification (self-attestation only for now)

## Boundaries & safety
- 18+ gated (self-attestation), for the romantic/sexual/intimate mode
- Somewhere accessible (about page, terms), it's disclosed clearly that this is AI, not a person
- If a conversation signals real distress or crisis, the companion should break character and point to real resources rather than staying in persona
- Explicit sexual content is allowed in the romantic/sexual/intimate mode for adult users, subject to a hard-coded, persona-proof exclusion list: no non-consent themes, no minor-coded characters, no real identifiable people — see SPEC.md §5
