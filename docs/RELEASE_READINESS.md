# QuizBlast Release Readiness — 28.09.2026

## Current decision

The code is integrated into `main` and tested in CI. No production service has
been deployed and no new MASTER version has been assigned. Activation requires
a selected host, public URL, TLS ingress, and a production configuration. Do not
run the repository's default Docker Compose file on a public host: it publishes
PostgreSQL, Redis and backend ports, uses example database credentials, and is
configured for localhost.

## Preconditions for an activation candidate

1. Choose the hosting platform, public HTTPS domain, persistent PostgreSQL volume,
   backup storage, and operator. Record the exact `main` commit and successful CI run.
2. Provide deployment configuration through the platform's secret manager: unique
   high-entropy `SECRET_KEY`, non-example database credentials, actual
   `DATABASE_URL`, and exact HTTPS `CORS_ORIGINS`. Never upload a real `.env`.
3. Terminate TLS at a trusted ingress. Forward the browser origin to the frontend
   nginx container, including WebSocket Upgrade for `/ws/`. Verify HTTPS API
   `/api/` and WSS `/ws/` end to end. Keep PostgreSQL, Redis and backend ports
   private. The current frontend nginx listens on HTTP internally; TLS ingress is
   a separate deployment component.
4. Run exactly one backend process/container. In-memory room sessions, timers,
   broadcasts and authentication rate limits cannot be split across workers.
5. Back up PostgreSQL and document restore procedures before the first deployment
   or schema change. The application uses `create_all` and has no versioned
   migration/rollback framework. Keep the previous image and configuration for
   rollback; restoring an older app against a changed schema requires a reviewed
   database restore plan.

## Automated gate

- On the exact candidate commit, require successful GitHub CI: Compose validation,
  image builds, backend regression modules, actual host/player/display flow,
  backend restart recovery, Playwright browser recovery, and nginx SPA fallback.
- Treat a successful CI run as evidence for the CI environment. It does not
  establish external TLS, production secrets, public network isolation, backup
  restoration or behavior on physical devices.

## Physical acceptance on the selected host

Use separate browsers/devices for host, two players and display. Record the URL,
commit, environment, tester and PASS/FAIL for each line.

| Gate | Action | Pass criterion |
| --- | --- | --- |
| Transport | Open public URL via HTTPS; join from another device | All API requests are HTTPS; game sockets use WSS; no mixed content |
| Ownership | Log in as host and another user | Other user cannot control or list host's rooms |
| Gameplay | Start a quiz, answer on both players, reveal result | Timers, scores and display agree with server state |
| Host return | Disconnect host during a question; wait; reconnect | Timer stays paused and resumes with preserved scores |
| Browser loss | Clear host browser storage; log in again | Host finds own open room and returns to it |
| Restart | Restart the single backend while room is active | Room and player sessions recover without losing accepted answers |
| Closure | Close room as host; attempt reconnect | Room rejects joins; no active room is closed automatically |
| Storage | Check database volume, backup and recovery procedure | Data persists; restore procedure is documented and verified |

Closed rooms are deleted after 15 days; do not shorten the lifetime of active or
host-paused rooms to simulate this gate. The 15-day boundary is covered by tests.

## Activation and stop conditions

After every prerequisite and physical gate passes, record the approved image
and commit, take the final backup, deploy one backend instance, and run a short
HTTPS/WSS smoke test. Monitor logs and health after activation. Stop and roll
back application traffic if login, WebSocket connection, room recovery or
persistent database access fails. Do not mark the release complete without
confirming the rollback path and recording the actual production URL.

**Outstanding decisions:** hosting platform and domain, ingress/TLS, secret
management, backup/restore owner, release version and deployment window.
