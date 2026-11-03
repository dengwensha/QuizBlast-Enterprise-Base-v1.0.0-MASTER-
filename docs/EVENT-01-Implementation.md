# EVENT-01 — Private event drafts

## Scope
Authenticated owners can create, list, read and edit event drafts. No quiz/room/result changes.
Owner is the existing immutable User.id resolved from a valid JWT subject; client owner/status fields are rejected.
An additive event_drafts table uses the existing Base.metadata initialization, repeatable on existing databases.
PATCH uses revision matching in its SQL UPDATE; stale writes return 409. Lists are owner-scoped, bounded and ordered by created_at/id.
Dates require an explicit timezone, persist as UTC and display in device local time. Null clears a schedule; omitted PATCH fields remain unchanged.

## UI-LIVE overlap check
Base: feature/QB-UI-LIVE-01D-invite-sharing at 739ce3d84e931b1473a866b605d02bfb89cd421e (PR #17).
Head rechecked before implementation delivery; no change observed.
App.jsx: added import, authenticated menu action and event screen only; QR popup, arrival animation, fullscreen, question progress and invitations retained.
main.py: registered separate event model/router only; game endpoints and WebSocket payloads unchanged.
http_perimeter.py: added PATCH to explicit CORS method list for the new endpoint.
ci.yml: added event backend module and browser suite; retained every UI-LIVE test and recovery gate.
The event draft PR targets the UI-LIVE tip, not main. CONTENT-01D acceptance and the documentation-only PR #18 remain separate.
No CONTENT V3 draft commits were copied into this implementation.

## Verification
Local: production frontend build; node game-clock tests; all 21 backend modules listed in CI on SQLite; event HTTP suite (6 tests including production model registration and repeated schema initialization).
Browser tests cover list error/retry, empty state, create, refresh, edit, stale revision/reload, cleared date, navigation and anonymous entry protection. Local Chromium download failed; browser execution and PostgreSQL/Docker gates must be verified in GitHub CI.
SQLite regression is not a substitute for the PostgreSQL CI gate.
No merge or deployment. Physical acceptance remains pending.

## Physical acceptance
Log in as A: create/edit a draft; refresh and reopen; verify the local date.
Log in as B: A's draft is absent; direct API GET/PATCH to A's ID returns 404.
Edit the same draft in two tabs: first save succeeds; second reports conflict and preserves unsaved input until the user opens the current record.
Verify existing Host/Player/Display, QR invitation sharing and education catalog flows.
