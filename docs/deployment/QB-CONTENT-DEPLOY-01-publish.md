# QB-CONTENT-DEPLOY-01 — Controlled first catalog publication

Status: **CI gate pending**. No Render environment variables or database records modified by this sprint.

## Exact scope
- Existing verified content: `backend/app/content/initial_sets_v1.json`, four named sets with six questions each.
- Startup publisher defaults to **disabled**; only `QB_PUBLISH_INITIAL_CONTENT=publish-v1` enables publication.
- `publish_if_requested` validates **all 24 questions first**.
- Creates four centrally owned published sets and their 24 questions in the same existing startup transaction.
- If all four catalog slugs already exist, verifies ownership, version, published status and counts before returning `already_published`, without changing them.
- If any slug already exists but the collection is incomplete or structurally different, raises an error and prevents startup; requires manual inspection.
- Existing user-owned quizzes, questions and import records are never deleted or overwritten.
- CI checks disabled/no-write, enabled/24, duplicate/no-change, mismatched/fail-closed, and rollback.

## Deployment process after full CI PASS
1. Confirm the existing Render Free web service runs the exact CI-passed branch; keep Auto-Deploy disabled.
2. Check `GET /api/content/sets` first: if populated, STOP and review; do not enable seeding.
3. Temporarily set `QB_PUBLISH_INITIAL_CONTENT=publish-v1` on **quizblast-enterprise-temp only** (never in source control or unrelated environments).
4. Redeploy manually, then verify logs report `Initial catalog: published` (or `already_published`), and `GET /api/content/sets` returns exactly four sets and 24 total questions.
5. **Remove the flag immediately** and apply environment change (may require restart/redeploy); verify catalog remains, without new records.
6. Physically test catalog, preview privacy (no correct answer or explanation), Play and Copy on isolated test database.
7. Record result, and keep test database expiry (**2026-11-15**) visible for backup/removal planning.

## Safety notes
- Render database external IP allowlist is currently empty. Do not open it just to seed content.
- Never expose `SECRET_KEY`, database URLs, or SQL credentials in chat, code, logs or screenshots.
- Restart will interrupt active game sessions. Schedule publication **after** physical play sessions.
- No Railway changes, paid resources, production operations, or UI/game engine modifications.
