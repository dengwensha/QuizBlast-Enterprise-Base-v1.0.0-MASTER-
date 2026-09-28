# CHANGELOG

## Unreleased — feature/QB-233-T001-ui-foundation

These changes are on the development branch and have not been released on `main`.

### Frontend and deployment
- Extracted game, admin, quiz, auth, and import components, hooks, and request services from the original App implementation.
- Added shared UI components and removed the unused `xlsx` dependency.
- Added a production frontend image using a build stage and nginx, pinned backend dependencies, and CI checks for builds, backend regression, restart recovery, and browser recovery.

### Security and data integrity
- Authorized host HTTP controls and WebSocket connections; changed state-changing game controls to POST.
- Revalidated import files on the server when committing, enforced exact CORS origins, and added process-local login and registration rate limits.
- Checked answers and time limits on the server; protected quizzes and questions used by active rooms.

### Game recovery
- Persisted room and player state in PostgreSQL, paused questions when the host leaves, and restored active rooms after backend and browser restarts.
- Added player reconnect credentials, room instance identities, host reauthentication, and a way for a host with cleared browser storage to find and rejoin their own open rooms.
- Added explicit host room closure and deletion of closed rooms after 15 days. Active and paused rooms do not expire automatically.

### Current limits
- Live rooms and authentication rate limits require a single backend process; Redis does not synchronize them. See the deployment limit in README.md.
- No JWT revocation or refresh flow and no database migration framework are in place.
- AI question generation is template based; browser alert, confirm, and prompt dialogs remain in parts of the interface.

## QuizBlast Enterprise Base v1.0.0 MASTER

### Added
- Official MASTER baseline structure.
- VERSION file.
- Release notes and stabilization report.
- QES task numbering standard document.

### Stabilized
- Backend Python compile verified.
- Frontend npm build verified.
- Manual backend golden tests verified after schema adjustment.
- QBDS DTO relaxed so Validation Engine can own row-level validation errors.
- Database session helper now rolls back on exceptions.
- Removed generated cache/build artifacts from release package.

### Known Limitations
- At this original baseline, frontend logic was largely inside `App.jsx`.
- Browser `alert()`/`confirm()` dialogs existed and a dedicated Import History screen was still planned.
