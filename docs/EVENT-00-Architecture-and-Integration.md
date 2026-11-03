# EVENT-00 — Event Studio architecture and integration contract

Date: 2026-11-04
Status: discovery complete; implementation pending.
This document does not close CONTENT-01D, approve publication, or authorize merge/deployment.

## Evidence and branch isolation

Documentation base: feature/QB-CONTENT-01D14-isolated-preview at 4d8cbfa43286c669aff8ba96cc69f529cdf936cc.
UI-LIVE tip inspected: feature/QB-UI-LIVE-01D-invite-sharing at 739ce3d84e931b1473a866b605d02bfb89cd421e.
These histories diverge: UI tip is 14 commits ahead and 59 behind the CONTENT tip; merge base is 075733b8d2fb7bf20734429199e3ab76f24ded09.
Commit counts are ancestry evidence, not conflict counts. No trial merge or build was performed for this documentation change.

UI-LIVE PR chain: #13 -> #14 -> #15 -> #16 -> #17.
Each targets the preceding feature branch (the first targets UI-10A).
Do not treat these as five independent changes or assume main contains them.

## Product goal

First paid pilots: event organizers and companies.
Education remains a parallel acquisition channel on the existing content/game infrastructure.
MVP: one account owner prepares one event with one quiz and one game session, runs it using Host/Player/Display, and retrieves its final summary later.

## Verified reusable infrastructure

- Authenticated Host controls with room ownership; anonymous Player PIN/nickname and Display entry.
- Existing lobby, start, pause/resume, question/result/leaderboard and completion phases.
- PostgreSQL room/player state, instance identity, reconnect/restart recovery and server-authoritative timing.
- Published quiz play, personal quiz copy, images, alternative text and optional explanations.
- Closed rooms are purged after 15 days: an event result must not depend on retained room rows.
- Runtime sockets/tasks and game state dictionaries remain process-local; no multi-instance support is assumed.

## Delivery sequence

### EVENT-01: event draft and ownership

Only create/list/read/update event drafts and the basic authenticated list/editor.
Fields: stable event_id, server-derived owner, title, optional organization label, optional timezone-aware scheduled time (UTC persistence), created/updated timestamps.
Organization label does not grant organization membership or shared access.
No quiz selection, room creation, result persistence, deletion or game controls in this step.
Missing/expired authentication: 401. Foreign/nonexistent event: indistinguishable 404.
Reject blank titles and invalid timestamps; never trust a client owner field.
Acceptance: cross-account isolation, persistence across refresh/restart, invalid input rejection, unchanged existing game and education flows.

### EVENT-02: quiz and one session

Allow owned quizzes or published central sets only.
Event-to-room link and room creation must commit atomically; serialize concurrent requests and enforce one session per event in the database.
Repeated requests return the same session. Creating the room never starts the game.
Quiz selection becomes immutable once a session exists.
Use an independent stable event identifier and room instance identity; PIN is only an invitation code.
Prevent restart through every existing start endpoint for an already completed event session.
Existing standalone games retain their behavior.
Acceptance: concurrent requests create one room, foreign/unpublished quiz rejection, refresh finds the session, no automatic start, no privilege escalation.

### EVENT-03: durable final summary

Freeze further answer acceptance and persist completion plus a single immutable result in one transaction.
Normal completion and early termination preserve accepted scores; record completion reason.
Closing an unstarted session records cancellation without a final ranking.
For a running event, finalization must succeed before room closure; failure must remain retryable.
Persist event/session identity, quiz title, question totals, revealed-result count, unique admitted-player count, nicknames, scores and completion timestamp/reason.
Do not copy authentication tokens or token hashes into results.
Equal scores share rank. Disconnected admitted players count as participants.
Results survive room closure and room-retention purge. No cascading room deletion may remove them.
Acceptance: answer/finalization race, duplicate requests, persistence failure, restart and purge; owner-only result access.

## Shared-file conflict gate

Before ANY shared-file modification:
1. Read fresh heads and all open UI-LIVE PR file lists.
2. Compare intended event base with the current UI-LIVE chain; inspect overlapping hunks and dependent behavior.
3. Record the exact base SHA, UI SHA and resolution decision in the event implementation PR.
4. Preserve QR popup, invitation sharing, arrival animation, fullscreen/stage layout, question progress, guest entry and reconnect behavior.
5. Verify with build/full regression and targeted browser tests after integration. Refresh this check if either head changes.
A clean textual merge alone is insufficient.

| Shared path | UI-LIVE ownership observed | Event handling |
| --- | --- | --- |
| frontend/src/App.jsx | PRs 13, 14, 15, 16 | Add only authenticated event navigation after fresh hunk/behavior review |
| backend/app/main.py | PR 16 | Review game-stage payloads; add event adapters without changing game semantics |
| frontend/src/hooks/useGameSession.js | PR 16 | Keep outside EVENT-01 scope |
| .github/workflows/ci.yml | PRs 13, 15, 16, 17 | Preserve existing gates; add tests only after checking current workflow |
| frontend/tests/recovery.spec.js | PR 16 | Preserve existing recovery scenarios |
| docs/UI-LIVE-01.md | PRs 13–17 | Leave untouched; event documentation stays separate |

Proposed new files (not created by this PR):
backend/app/services/event_store.py, backend/app/schemas/events.py,
frontend/src/services/eventService.js, frontend/src/components/events/EventStudio.jsx,
and focused event tests.
Final structure must follow the freshly inspected implementation base.

## Open decisions and boundaries

- Choose result retention duration and owner deletion semantics before EVENT-03.
- Verify immutable question ordering/content while an event session exists.
- Choose an accepted integrated implementation base; this documentation base is not an integration/release approval.
- CONTENT-01D physical/editorial acceptance remains a separate workstream.
- Build and full automated tests are mandatory for implementation; physical pilot acceptance requires at least 10 real participants against the 10–25 participant target.

## Out of scope

Slides, polls, AI generation, multi-round programs, cross-round scoring, teams, multiple presenters/displays, company roles, payment/subscription, ticketing, advanced reporting and extensive branding.
No production code, schema migration, content publication, merge or deployment in EVENT-00.
