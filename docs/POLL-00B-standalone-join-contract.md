# POLL-00B — Standalone participant join, identity and cohort contract

Status: Verify-First discovery / documentation only. 2026-11-23.
Target: Poll Studio live demonstration 2026-12-12.
Base: POLL-00A documentation commit a5aa5a5 atop 28f27f8. Before implementation compare active Event Studio + slide-remote heads. No production edits, DB schema, merge or deploy.

## Verified current implementation
- `frontend/src/App.jsx`: quiz invites use `?pin=...`; anonymous players bypass account login, but join triggers existing quiz-mode state and active-session restore in local/session storage.
- `backend/app/main.py` WebSocket `/ws/{room_pin}/{player_name}`: demands live quiz room, matches instance_id, enforces nickname/reconnect token and creates GamePlayer in GameRoom. It is NOT suitable for poll-only sessions without adaptation.
- `backend/app/services/game_recovery.py`: GamePlayer primary key = (room_pin, name), reconnect token hash; closed-room retention deletes players after time. Quiz nickname alone cannot guarantee immutable poll identity.
- `frontend/src/services/api.js`: public QR/link origin uses VITE_PUBLIC_APP_URL or window origin. Poll invite must retain reachable origin for LAN and hosted usage.
- `backend/app/routes/event_games.py`: EventRun has owner commands and separate read-only Display credential, but is not required for standalone Poll Studio.
- POLL-00A standalone module owns definition, session, voting, basic analytics and report. Event Studio gets optional adapter only.

## Decision: two credentials, neither is quiz credential
1. **Public invitation**: owner shares an opaque, random poll-session invite code via HTTPS URL/QR. Invite code resolves to limited public poll metadata and join endpoint, **not** vote or management authorization. Avoid guessed sequential IDs as public capability.
2. **Participant credential**: on join, server creates high-entropy participant secret, stores its digest, and binds it to immutable participant_id + poll_session_id or explicit Poll Studio participation scope. Client stores secret locally for reload; does not place it into the QR, URL, Display state, logs or analytics. No account required. Credential should only be used over HTTPS outside localhost.
3. **Owner credential**: existing authenticated user token for create, open, close, report. Never reuse invite or participant token for owner commands.
4. **Display credential**: separate read-only capability restricted to public aggregate projection. No raw votes or participant secrets.
5. **Event Studio adapter**: optional event_id/step_id binding references a Poll Studio session. The adapter does not mint GameRoom, Quiz PIN or quiz-score objects.

## POLL-01B hard gate — duplicate registration prevention (2026-11-23)

- **Same participant + same poll session: one registration and one counted vote.** Reopening a QR link, browser F5, reconnecting, double-clicking Join, retrying after a timeout, or parallel Join requests must restore/return the existing participant record rather than insert a new one whenever the participant credential is available.
- A server-issued, opaque **join idempotency key** is persisted by the client before the initial Join attempt and included with retries. Server records a unique scope-and-key mapping and responds with the same participant identity for identical attempts, including simultaneous requests; client-side button disabling is not sufficient.
- Existing participant token takes precedence over creating a new identity; authenticate it against the exact poll session. A wrong-session token must fail closed and must not be silently replaced.
- Database-level constraints for participant registration idempotency and for `UNIQUE(poll_session_id, participant_id)` on votes are mandatory, with atomic conflict handling. Duplicate same-option vote retries are idempotent; different-option retries return 409.
- **Nickname is display metadata, not a person identifier**. Rejecting a repeated nickname alone is neither secure nor sufficient, and can allow an attacker to block a legitimate participant. Rate limiting and abuse monitoring help deter repeated anonymous registrations.
- **Limit of the December anonymous QR MVP:** loss of browser credential/storage, incognito browsing or a second physical device can produce a new anonymous identity. It is impossible to guarantee one human one vote without a stronger identity/verification method (e.g. authenticated invitation or one-time attendee credential). Do not claim such a guarantee.
- Acceptance: verify repeated QR open, double join, F5/restart, two concurrent join requests, same token in second tab, same nickname across independent participants, and vote-level duplicate submission. Distinct participants must not be unintentionally merged.

## Proposed join and resume behavior
- Host starts standalone Poll Studio session and shows QR/link `/poll/join?invite=<opaque>`.
- Player opens URL without login. GET limited public state; on explicit join POST with optional display nickname. Server returns participant token only to that client; save it to client storage indexed by poll session, not shared host auth storage.
- On F5/reload, restore with saved token via `GET /poll-sessions/{id}/me`; server verifies digest and session scope. Preserve already-voted receipt; UI must not offer another mutable vote.
- If storage was cleared, treat user as a new identity. Browser-only identity does not prevent a determined human from voting again on another device/private mode. Never advertise one-person-one-vote as a proven property: MVP guarantees **one vote per server-issued participant identity per poll session**. Strong person-level uniqueness requires stronger registration and privacy tradeoffs.
- Optional nickname is not identity or uniqueness key. Same nickname can be used by different participants without taking over the session.
- Join should be possible while poll is open; late participants can vote before close. After close, show non-editable result/closed message and reject new votes; precise access policy for joined voters must be consistent.
- Unavailable/invalid invite has explicit error; no silent redirect to Quiz join. Rate limit joining and vote attempts, constrain text length and sanitize display fields. Prevent public responses containing session owner data.

## Server invariants and race protection
- Unique DB constraint `(poll_session_id, participant_id)` on vote rows and scope-safe FK; do not rely on client disabling buttons for uniqueness.
- Transactionally verify active status, option belonging to pinned poll definition version, participant credential/scope, and session revision/closure. Concurrency with closing must have a consistent ordering (lock or compare-and-swap); never accept post-close votes.
- Identical retry returns prior accepted receipt without increment; different selection returns conflict and no mutation; concurrent conflicting submissions leave exactly one durable vote.
- Client refreshes only read-only aggregates, with revisions or snapshots from backend; no local tally as source of truth.
- If a poll session is relaunched, create a new session ID, not reset previous votes. Definition version is frozen when opened.

## Participation denominator decision for December
- Distinguish `eligible_audience_count` (all people entitled to participate) from `registered_participant_count` (server-issued poll identities joined by close) and `valid_vote_count`.
- With open public QR and late join allowed, whole-event eligible audience E generally cannot be proven. Set `audience_participation_rate = null`; never imply a total event audience from browser connections or nicknames.
- MVP can report **response rate among registered poll participants** at closure: `valid_vote_count / registered_participant_count` when denominator > 0; label exactly `Ankete katılan kayıtlı kullanıcılar içinden oy veren oranı`. Registered count is frozen at close and must include all valid voters. During open poll, rate is provisional and clearly labeled; 0 denominator => null.
- Report separate vote counts, option percentages (denominator = valid votes), registered count and optional configured event-attendance count only if independently supplied and clearly sourced. No inflated non-voter claim for the entire audience.
- POLL-00A's earlier 'freeze at open / reject late join' suggestion is superseded for the December demo. Revisit true cohort-based analysis later with explicit event roster.
- No demographic data collected for future regression. Keep immutable identifiers/version, accepted_at, minimal audit metadata and retention under approved deletion policy only.

## Proposed minimal HTTP contract (not implemented)
- Owner: POST /polls, POST /polls/{poll_id}/sessions, POST /poll-sessions/{id}/open, POST /poll-sessions/{id}/close, GET /poll-sessions/{id}/report.
- Public: GET /poll-invites/{invite}, POST /poll-invites/{invite}/join (returns participant token over HTTPS).
- Participant: GET /poll-sessions/{id}/me, POST /poll-sessions/{id}/votes with participant bearer token + option_id.
- Display: GET /poll-sessions/{id}/aggregate with separate display credential and narrow projection; consider embedding safe aggregate in Event Studio display projection.
- Error examples: 401 invalid participant credential, 404 unknown/foreign scope, 409 closed/duplicate altered vote/stale state, 422 bad option. Exact payload names and schema await POLL-01A.

## Acceptance matrix / minimum test set
1. Standalone poll can be created and launched without EventDraft or GameRoom.
2. Owner only can start/close/edit before open; foreign owner and participant cannot perform admin operations.
3. QR invite resolves anonymously and joins without Quiz PIN; expired/invalid invite fails.
4. Two participants with same nickname get different IDs; neither can use other's token or scope.
5. F5/reconnect returns existing participant and vote receipt; backend restart preserves both.
6. Two rapid/concurrent vote requests for same participant result in exactly one committed row, including differing options.
7. Same vote retransmission is idempotent; different option refused.
8. Unknown option, cross-session token, vote-before-open and vote-after-close rejected.
9. Late join during open accepted; close creates frozen registered count, all valid votes <= registered count.
10. Display sees aggregate only. Counts add up exactly; zero votes, ties and undefined denominator do not display misleading percentages.
11. Owner report persists until explicit expiry; quiz room purge cannot delete poll report.
12. Existing Quiz join, WebSocket, Event Studio and Slide Remote tests remain unchanged and green.
13. CI includes backend/Postgres integrity and 390px mobile Playwright flow, F5 and double-submit; physical multi-device rehearsal separate.

## First implementation micro-sprint (POLL-01A)
Single target: poll definitions and durable standalone session schema + owner-only create/read contract, backed by isolated tests. No join, votes, Display, Event Studio wiring, frontend changes or migrations to unrelated tables.
- Verify exact current branch head and migrations/startup registration strategy before patch.
- Add server-owned poll definition, bounded 2–6 option list, immutable IDs, owner authorization; distinguish definition ID from session ID.
- Test invalid options, owner isolation, stale version, restart persistence and safe schema initialization.
- Gate: unit/DB tests, production build if affected, exact CI commit, clean git, no merge/deploy until review.
