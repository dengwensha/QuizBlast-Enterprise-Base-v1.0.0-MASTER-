# QuizBlast Enterprise Base v1.0.0 MASTER — Release Notes

## Purpose
This is the first official MASTER baseline for QuizBlast Enterprise.

## Included Functional Scope
- FastAPI backend
- React/Vite frontend
- PostgreSQL and Redis via Docker Compose
- Register/Login with JWT
- Quiz management
- Question management
- WebSocket multiplayer game flow
- Excel/QBDS preview pipeline
- Validation engine
- Duplicate detector
- Import report/preview engine
- Import Commit endpoint
- Import History endpoint

## Stabilization Changes
- Removed generated artifacts from package.
- Added VERSION and CHANGELOG.
- Added release notes and QES task standard.
- Relaxed QBDS DTO field restrictions so row validation is reported by Validation Engine instead of failing early in mapper.
- Added rollback behavior to `db_session()`.

## Verification
- `python -m compileall backend/app` passed.
- Frontend `npm run build` passed.
- Manual backend golden tests passed.

## Next Sprint
Sprint 2.3.3 — Enterprise UX
- QB-233-T001 UI Foundation & Frontend Refactoring
- QB-233-T002 Dashboard Header
- QB-233-T003 Enterprise Question Grid
- QB-233-T004 Search & Filter
- QB-233-T005 Enterprise Modal
- QB-233-T006 Import History UI
