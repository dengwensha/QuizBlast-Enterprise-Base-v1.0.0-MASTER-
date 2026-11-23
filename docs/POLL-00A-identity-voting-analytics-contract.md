# POLL-00A — Poll identity, voting, analytics and trust contract

Status: proposed architecture / documentation-only. Target event: 2026-12-12. Baseline: `28f27f8` (PR #52); verify freshness before any implementation. No production code, database migration or deployment in this step.

## Verified baseline
- `backend/app/schemas/events.py`: `AgendaStep.kind` currently accepts presentation, quiz, break only; `EventAgendaUpdate` uses optimistic event revision and max 50 steps.
- `backend/app/routes/event_games.py`: program `Run` snapshots steps, uses cursor/view/revision and owner authorization; Display reads separate display credential and polls state.
- `backend/app/services/event_store.py`: agenda/run store JSON steps; EventReport and EventStepReport persist quiz ranking with expiry; program retention is a separate preference.
- `backend/app/services/game_recovery.py`: quiz player identity is scoped to room PIN plus name, with separate hashed reconnect token; closed-room cleanup eventually deletes players. Do not infer reusable poll eligibility from a quiz nickname or ephemeral live roster.
- Frontend: EventAgenda and EventLive have explicit step-kind switches; all must be audited for a fourth kind, including generic program transitions, display and stage sizing.

## Locked MVP intent / explicit non-goals
- One question per poll, single-choice, 2–6 choices, no correct answer, no score.
- Multiple poll steps in one event are permitted only if each is given an immutable step ID and isolated poll session. At least one poll step must work on December 12.
- Owner can define poll in agenda, open voting, close voting, and reveal aggregate results on Display. Owner-only post-event report.
- No free text, multi-select, demographics, AI interpretation, exports or answer editing in MVP.
- Quiz gameplay, scoring, existing PIN/QR join and private reports must not change. Avoid assuming that a quiz room exists for a poll-only event.

## Identity and authorization
1. `PollParticipant`: server-generated stable random participant ID and a high-entropy bearer token; database stores token digest only. Identity scoped to event, not nickname. Restore it across refresh from the token; nickname is optional presentation metadata and never an authorization key.
2. Join entry point may reuse the existing event invite UI/QR presentation, but requires a separate poll/event join protocol. Existing quiz PIN and room must not be required for a poll-only event. Never expose owner or Display credentials.
3. A poll vote requires valid participant token, matching event/poll session and active poll state. Host actions require existing authenticated event owner authorization. Display obtains aggregate state only using event Display credential.
4. For one poll session, unique `(poll_session_id, participant_id)` at the database level. First successfully committed vote is immutable for MVP. Retry of the exact same selection may return 200 with the previously accepted receipt; a different selection returns 409. Concurrent submissions and restart must not create two votes.
5. No votes accepted before opening, after closing, from another event, or with revoked/unknown credentials. Public state must never disclose individual votes, token hashes, participant IDs or raw answer rows.
6. Poll definition becomes immutable when session opens; stale versions fail with 409. Owner cannot delete or mutate active/finished poll content in a way that reinterprets prior votes.

## Proposed logical data model (NOT IMPLEMENTED)
- `PollDefinition`: id, event_id, immutable step_id, question, ordered options with stable option IDs, owner_id, version.
- `PollParticipant`: id, event_id, token_digest, joined_at, optional display_name; event participant credential independent of quiz room.
- `PollSession`: id, event_id, step_id, poll_definition_version, status (draft/open/closed), opened_at, closed_at, revision, display_results flag.
- `PollVote`: id, poll_session_id, participant_id, option_id, accepted_at; unique(poll_session_id, participant_id). Foreign keys and integrity checks required.
- `PollSummary`: proposed retained, derivable report snapshot with event_id, step_id, session_id, closed_at, eligible_count (nullable), vote_count, option counts, expires_at, participant_count_source. No individually identifying data needed in aggregate report.
- Exact columns/migrations and cleanup policy deferred to POLL-01A; do not duplicate event data where stable references suffice. Retention must remain independent of purged quiz rooms.

## State machine and consistency
- Agenda -> open poll step -> voting open -> close poll -> reveal results -> complete step -> agenda.
- Owner commands are revision-checked and atomic. A stale command is rejected with 409. Results are calculated from committed votes; Display never tallies locally.
- Snapshot poll definition at open so reordering an agenda never maps votes to a different question.
- Participant token and poll session identity must survive F5/reconnect and backend restart. Never silently retry a rejected vote with a different participant identity.
- Decide whether the poll can be reopened; proposed MVP: cannot reopen a closed poll session, reducing double-count and result integrity risk.
- Display update can initially use existing 1-second polling pattern; test concurrency and visibility with multiple clients.

## Analytics contract and mathematical invariants
- Total valid votes N = count of committed unique participant votes in that session.
- Per-choice count n_i >= 0; sum_i(n_i) = N; per-choice percent = 100*n_i/N when N>0, otherwise show zero-vote empty state without dividing.
- Top option is all tied maximum options; no fabricated unique winner in a tie.
- Eligibility denominator E is the server-captured unique count of participants eligible when the poll opened, with a documented capture source. If eligibility cannot be established reliably, return null for participation rate and non-voters (do not label current live connection count as eligible).
- When E is valid and N<=E: participation percent = 100*N/E; non-voters = E-N. If late arrivals are allowed, eligibility cohort and denominators must be redefined before percentages are shipped. Proposed December scope: snapshot cohort at opening and enforce it for voting; do not permit uncounted late arrivals to distort E.
- Aggregate report must include event/step/poll identifiers, title, options, counts, N, E/null, percentage calculation version, opened_at, closed_at, expires_at and retention policy; no personal answers in Display.
- Define rounding in presentation only, e.g. one decimal place; raw counts are source of truth. Percentages may total 99.9/100.1 due to display rounding. Tie and zero-vote scenarios must be explicit.
- Owner-only report remains accessible after event and backend restart until defined expiry. Verify existing quiz report defaults versus presentation retention choices before selecting poll expiry. Do not assume all existing data is 15 days.

## Minimal API outline (proposed, not existing)
- Owner: `PUT /events/{event_id}/polls/{step_id}` (definition, revision), `POST /events/{event_id}/polls/{step_id}/open`, `POST .../close`, `GET .../report`.
- Participant: scoped poll join/restore endpoint; `POST /poll-sessions/{session_id}/vote` with participant bearer and option ID.
- Display: aggregate poll status via existing program-state trust boundary or narrow read-only endpoint requiring display credential.
- Define exact payloads and route conflicts after mapping existing `/events/{event_id}/...` routes. No unguarded public vote or report endpoint.

## Test-first acceptance matrix
1. Owner can create a single-choice 2–6 option poll; invalid option counts, duplicate IDs, empty labels and cross-event IDs rejected.
2. Event agenda accepts poll; repeated IDs and stale revision rejected; moving/reopening keeps poll reference stable.
3. Anonymous poll-only join through scoped invitation and refresh preserves the same participant; nickname collision alone cannot override identity.
4. Same participant same poll: first vote accepted; identical retry no duplicate; changed vote rejected; two parallel votes yield one committed row.
5. Unknown, revoked, cross-event tokens, invalid options and closed polls rejected; owner auth enforced; Display sees only aggregates.
6. Zero votes, ties, sum of counts, percentage precision, denominator snapshot/unknown policy and no misleading rate are validated.
7. Host/Display see same revision and totals after reconnect/restart; old quiz, slide remote and report tests remain green.
8. Owner report persists, obeys expiry and protects private data.
9. Browser: at least one real phone-like viewport poll submission, double-click and F5 recovery with mocked API; full multi-device physical validation scheduled separately.
10. CI: production build, backend tests (Postgres), browser regression; exact passing commit captured. No merge/deploy without gates.

## Implementation dependency/order
- POLL-00B: verify join/restore and source-of-truth attendance (highest risk); test-only or documentation first.
- POLL-01A: new schema and owner-owned definition API, contract tests.
- POLL-01B: poll-only participant join, identity and atomic voting.
- POLL-01C: Event Run host controls and read-only Display aggregates.
- POLL-01D: summary snapshot, owner report and expiry.
- POLL-01E: full regression, 10+ participant local acceptance, live rehearsal.
- Stay on isolated branch/stacked PR; compare current Event Studio head with slide-remote PR #52 and test PR #53 before any shared App, EventLive, routes, models or CI edits.

## Open decisions before implementation
- Poll-only entry: event-specific QR/token vs shared multi-step event join link; favor event-specific join that works without a quiz room.
- Cohort: server-frozen eligible roster at opening vs admit late participants. MVP recommendation: frozen roster, with explicit no-vote state if roster unknown. Confirm real user flow.
- Result visibility: keep results hidden until Host reveals; proposal preserves independent control.
- Retention: proposed 15-day owner access if validated with existing report policy; must define source, expiry and deletion semantics.
- Persistent participant scope: entire event versus each poll; recommend entire event token plus per-session unique votes.

Exit: architecture contract ready for review only; no implementation claimed.
