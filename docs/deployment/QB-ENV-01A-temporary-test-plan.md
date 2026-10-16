# QB-ENV-01A — Temporary Remote Test Environment (Verify-First)

Status: design/preparation only. No cloud resources, billing, database changes, or deployment are authorized by this document.

## Goal
Provide an on-demand, externally reachable environment for QuizBlast physical acceptance tests on Host, Player, and Display devices, followed later by a separate low-cost always-available staging environment.

## Verified repository baseline
- Source branch: `feature/QB-CONTENT-01-final-acceptance` (Final Acceptance CI #181 reported PASS).
- Four containers in `docker-compose.yml`: frontend (Nginx), backend (FastAPI/Uvicorn), postgres (16), and redis (7).
- `frontend/nginx.conf` currently proxies `/api/` and `/ws/` to Docker DNS `backend:8000`; this address cannot be assumed to resolve in a separately hosted service.
- Backend uses `DATABASE_URL`, mandatory `SECRET_KEY`, and `CORS_ORIGINS`. Frontend uses build-time `VITE_PUBLIC_APP_URL` for public links.
- Backend websocket endpoint: `/ws/{room_pin}/{player_name}`.
- Backend `main.py` currently has no Redis references; validate Redis necessity before provisioning it.
- Live room/socket state is process-local. Initial deployment must use exactly **one backend replica**, without autoscaling. App restarts may interrupt active rooms.
- Local Compose publishes postgres and redis ports and uses an example database password; **do not** reuse that exposure or credential in a publicly accessible environment.

## Minimal target topology
1. One public HTTPS origin for frontend + same-origin /api and /ws proxy.
2. One private backend instance (internal port 8000).
3. One private PostgreSQL database with isolated test records and persistent storage during acceptance.
4. Redis only if an explicit runtime dependency is proven.
5. No separate public database/Redis/backend endpoints unless required by an approved and reviewed design.

## First provider candidate
Railway (candidate, not locked). Verify current account-level pricing, free/trial credits, database persistence, service stop behavior, internal DNS, health checks, and WebSocket handling from authoritative live platform docs **before** enabling a paid resource. Keep Render as fallback. Do not assume that suspending compute suspends storage/billing.

## ENV-01B — Smallest required code/config changes (not part of 01A)
- Make Nginx upstream configurable or otherwise route to a verified backend private address without modifying the application game engine.
- Explicitly configure frontend `VITE_PUBLIC_APP_URL` for external QR/deep links.
- Set backend `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS` through provider secrets; no secrets in git.
- Ensure persistent PostgreSQL storage or an approved repeatable test-data rebuild.
- Define safe deployment start/stop procedures; deploy only the verified feature branch after CI PASS.
- Limit backend to a single instance; validate websocket upgrade, API proxy, health endpoint, mobile joins and cross-device behavior.

## Acceptance gates
- [ ] Provider and pricing verified; no chargeable resource created without user approval.
- [ ] Deployment-only changes scoped to a separate micro-sprint.
- [ ] Build + complete regression CI PASS for any code/config modifications.
- [ ] Only frontend reachable publicly; private backend/database networking verified.
- [ ] Test credentials and secret values kept outside source control.
- [ ] On-demand startup/shutdown verified, persistence and billing behavior explicitly recorded.
- [ ] Host/Player/Display physical acceptance including prepared content sets.
- [ ] Teardown/retention decision recorded after each test session.

## Out of scope
Production go-live, domain purchase, payment subscription, autoscaling, multi-instance game state refactor, Redis integration, UI/game engine changes, content publication, automatic deployment, database migration, and any provider account configuration in this step.

## Immediate next action
Review candidate provider live documentation and smallest deploy-only Nginx/config change (ENV-01B). Stop before provider account connection or paid provisioning, and request explicit approval.
