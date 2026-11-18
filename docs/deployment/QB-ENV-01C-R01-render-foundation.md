# QB-ENV-01C-R01 — Render Free deployment foundation

Status: **code and CI preparation only**. No Render web service, database, payment or public deployment was created.

## Verify-First decision
Render Free web services do not support private inbound network connections in the same way as Railway services. For physical test days use a single public Docker web service containing the built React UI, Nginx reverse proxy and one FastAPI/Uvicorn worker. Use separate Render PostgreSQL only after reviewing its Free plan limits and explicit user approval.

## Implementation
- `Dockerfile.render` is built from **repository root**, separately from existing backend/frontend Dockerfiles.
- `deploy/render/start.py` checks `PORT` (default 10000), transforms the existing `frontend/nginx.conf` into a localhost backend proxy and checks `nginx -t`. No other application sources are altered.
- Runtime supervises one localhost FastAPI process and one public Nginx process. The API and WebSocket share the same public origin.
- CI builds the Render Docker image and checks port/upstream substitution and Nginx syntax before the existing full regression.
- Original Compose/Railway deployment configuration and game logic remain unchanged.

## Manual Render setup after the CI gate
1. Create a **new**, isolated Render Free web service named `quizblast-enterprise-temp`. Do not modify previous `quizblast-v*` Render services.
2. Link the GitHub repository `dengwensha/QuizBlast-Enterprise-Base-v1.0.0-MASTER-` and branch `feature/QB-ENV-01C-R01-render-foundation`.
3. Use runtime Docker, repository root as build root, `Dockerfile.render` as Dockerfile path. Turn **automatic deployment OFF** for the temporary test service when supported; otherwise confirm before any push.
4. Allocate an isolated Free PostgreSQL instance; store the exact **internal connection URL** as `DATABASE_URL`. Do not use production data.
5. Configure `SECRET_KEY` using a newly generated strong secret stored only in Render environment variables; configure `CORS_ORIGINS` to the assigned exact `https://<service>.onrender.com` origin.
6. Only the Nginx `PORT` is public. Backend binds `127.0.0.1:8000`. Redis is not provisioned for this test.
7. Check HTTPS `GET /api/`, frontend home, QR links, and real WebSocket join from separate mobile and desktop devices.
8. Run the initial question-set publisher only against the isolated test database **after** explicit approval.
9. Expect idle suspension/cold start on Free; active game sessions may not survive suspension or restart. Avoid treating this temporary setup as production.

## Explicit limitations
- Render Free Postgres is time-limited and not a durable long-term staging datastore. Record expiration/backup strategy before use.
- Single process/replica for in-memory game room state; this is not a horizontal scale solution.
- Local `docker-compose.yml` does not change.
- CI image smoke tests check build and Nginx config; actual Render launch, PostgreSQL connectivity, and phone/tablet browser acceptance remain separate gates.
- On finishing tests: record resource state, delete or suspend ephemeral services by explicit decision, verify potential usage costs.

## Acceptance gate
Build and full CI PASS on this branch; no environment provisioning or actual deployment before service plan confirmation.
