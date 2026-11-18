# EVENT-02 — Quiz selection and one event session

## Base and acceptance provenance
Separate stacked implementation branch/PR on EVENT-01 beb81e669936ab125106d692961853fbe06f847d (PR #19).
The user completed EVENT-01 basic local physical acceptance on 2026-11-08: create, refresh/edit persistence, two-tab revision conflict/current record, account isolation and backend restart persistence.
UI-LIVE PR #17 remains at 739ce3d84e931b1473a866b605d02bfb89cd421e; common-file check refreshed before implementation. No merge/deploy.

## Behavior
An event owner selects an owned quiz or published central quiz with at least one question.
PUT /events/{id}/quiz requires the current event revision; choice is immutable once a session exists.
POST /events/{id}/session serializes on the owner-scoped event row and commits room + durable link together. A unique event primary key enforces one session per event. Repeated requests return that session, even if closed/purged; they never create a replacement room.
GET /events/{id}/game returns authorized choices and current session status. Event list labels derive from selection/room state; game phase is not duplicated on the event record.
The persistent link stores instance identity independently of room retention. Reused PINs cannot attach an old event to a new room.
Creation leaves a lobby; no timer/game task is started. Existing Host/Display and QR/share components are reused. Host starts manually. Completed event rooms reject restart at the existing backend start endpoint; standalone games retain restart behavior.

## Shared-file review
- main.py: extract transaction-aware RoomBuilder use and idempotent lobby initialization; add completed-event restart guard; order questions by ID. Existing authorization and game commands remain.
- App.jsx: only passes Host/Display navigation callbacks to Event Studio. Existing QR/stage/progress/invitation code untouched.
- events.py: adds the game subrouter and derived status rendering; draft ownership/revision controls retained.
- ci.yml: adds event-session backend module and browser suite; all previous gates remain.
- No changes to UI-LIVE components, transport hook, scoring or CONTENT draft files.

## Verification
Local frontend production build and complete CI-listed backend regression on SQLite. EVENT-02 tests exercise real production routes: ownership/quiz boundaries, empty quiz, simultaneous requests, rollback, retry after committed-response failure, closed/purged identity and PIN reuse, source editing freeze, manual start, Host/Player/Display, completed restart denial.
Browser scenarios cover desktop/mobile quiz selection, disabled duplicate submission, session restoration, QR invitation, Host transition and closed-session UI.
PostgreSQL, production Docker builds, full browser/recovery and Edge checks must pass on the final PR commit before technical acceptance. Physical acceptance remains separate.

## Physical acceptance
1. Use EVENT-02 branch in the isolated quizblast-event01 project (retain its volume/accounts).
2. Prepare a quiz in Admin, then event -> Quiz ve Oturum -> select/save quiz.
3. Create session: one PIN, lobby; no automatic start. Refresh/reopen: same instance/PIN.
4. Repeated requests/two tabs return the same session; quiz selection is locked.
5. Open Host, join Player and Display by existing PIN/QR flow, start manually and finish/end.
6. Completed event cannot restart. Closed event cannot create a second room. Another account cannot view/control it.

## Outside scope
Durable final summary/retention policy (EVENT-03), slides, polls, AI, multiple rounds, payment, merge and deployment.
