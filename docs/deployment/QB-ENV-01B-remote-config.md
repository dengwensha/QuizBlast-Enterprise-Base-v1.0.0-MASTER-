# QB-ENV-01B — Remote test deployment configuration

**Status:** Code/config only. No Railway account setup, infrastructure provisioning, data publication, billing or deployment has occurred.

## Scope
- Add a distinct frontend build at `frontend/Dockerfile.remote` while preserving original `frontend/Dockerfile` and `docker-compose.yml`.
- Remote Nginx config comes from `frontend/nginx.remote.conf.template`, rendered by the official Nginx image entrypoint.
- Environment substitution is restricted to `QB_BACKEND_UPSTREAM`; `$host`, `$scheme` and other native Nginx variables are preserved.
- CI builds and syntax-checks the remote image with a local dummy upstream; no cloud credentials are required.

## Candidate Railway service mapping (not deployed)
| Service | Source/build | Visibility | Environment |
| --- | --- | --- | --- |
| frontend | Source directory `frontend`; custom Dockerfile `Dockerfile.remote` | **public** HTTPS, internal port 80 | `RAILWAY_DOCKERFILE_PATH=Dockerfile.remote`; `QB_BACKEND_UPSTREAM=backend.railway.internal:8000` (verify actual service DNS name) |
| backend | Source directory `backend`; existing `Dockerfile` | private, port 8000, exactly **one** replica | `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS` |
| postgres | Managed private Postgres service | private only | Provider-issued credential URL; ensure storage retention policy |
| redis | Not initially deployed | n/a | Add only upon demonstrated runtime dependency |

**Critical:** Railway's Dockerfile path value is relative to the selected service source directory. Review the setting in the provider UI before deployment.

## Required pre-deployment configuration
1. Set `QB_BACKEND_UPSTREAM` to the internal backend hostname **and port** (no `http://`, no trailing slash), for example `backend.railway.internal:8000`.
2. Set `DATABASE_URL` to an isolated private test PostgreSQL database connection, never the production DB.
3. Generate an independent strong `SECRET_KEY`; do not write it into repository files or logs.
4. Set `CORS_ORIGINS` to the exact public HTTPS origin after assigned; no wildcard.
5. Frontend API/WebSocket URLs already use `window.location` same-origin. QR URLs also default to browser origin. Optional build-time `VITE_PUBLIC_APP_URL` should only be set if a deliberate external canonical URL is required.
6. Expose only frontend port 80 through the provider's public domain. Verify HTTPS, `/api/` and `/ws/` routing from separate devices.
7. Keep backend replicas at 1 because active rooms and sockets are kept in-process. No autoscale or unattended restart during physical tests.
8. Railway DNS visibility/start ordering must be tested: Nginx resolves its upstream at service start. Frontend may need a restart after the private backend is healthy.

## Verify-first checks
- CI: existing Compose build/regression remains untouched; CI additionally builds `Dockerfile.remote`, tests `nginx -t`, and checks substituted upstream and native variables.
- Deployment: health `GET /api/`, successful `/ws/` WebSocket upgrade, public QR join URL, mobile player+host+display sync.
- Shutdown: document what is stopped and whether persistent DB storage or provider plan continue incurring charges.

## Explicitly excluded
No payment, infrastructure creation, DNS/domain purchase, game engine code changes, Redis integration, database writes, or automatic promotion to staging.

## Provider reference
- https://docs.railway.com/builds/dockerfiles
- https://docs.railway.com/networking/private-networking
