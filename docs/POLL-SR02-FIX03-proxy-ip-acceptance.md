# POLL-SR02-FIX03 — Source-IP trust boundary and physical acceptance gate

## Scope and trust decision

- **Docker Compose:** Uvicorn is started with `--no-proxy-headers`, preserving the transport peer. The Poll join rate limiter may use `X-Real-IP` **only** when the transport peer resolves to the running `frontend` service on the internal Docker network. The NGINX `/api/` proxy overwrites incoming `X-Real-IP` and `X-Forwarded-For` with its own observed `$remote_addr`. Direct requests to the exposed backend port use their direct transport peer, not caller-supplied addresses.
- **Render:** The backend and NGINX are colocated, and upstream Render ingress may introduce additional hops. The Docker-only source-IP trust path does not claim to validate Render's true end-user IP. Before production, inspect Render's actual forwarded header chain and identify only the authentic trusted ingress addresses. Do not add wildcard `FORWARDED_ALLOW_IPS=*`, trust arbitrary `X-Forwarded-For`, or guess an ingress CIDR.
- This is a best-effort per-source-IP anti-abuse control, **not one-person-one-vote**. Shared NAT/Wi-Fi can legitimately share one quota. The process-local limiter requires a shared store if deployment becomes multi-worker.

## Acceptance — local physical test (required)

1. With the current Compose images, verify `frontend` and `backend` use the same internal Docker network. Confirm frontend container DNS resolution from backend.
2. From two genuinely different networks (e.g., Wi-Fi and mobile data), join the same Poll session through the **frontend** URL; test that both participants are able to join. Verify the effective source address using temporary diagnostic access logging **only in a controlled test environment** (do not log bearer credentials, join keys or invite URL).
3. Confirm direct backend `:8001` requests with forged `X-Real-IP` / `X-Forwarded-For` cannot impersonate arbitrary source addresses. Treat any unexpected trusted peer as a STOP.
4. Test up to 25 legitimate participants and reconnects; record any 429 responses. If all participants share a real observed NAT address, a shared quota is expected. Raise `POLL_JOIN_MAX_NEW_IDENTITIES` for the test only if needed and document the change.
5. Verify Quiz/GameRoom/Event traffic and Display behavior unchanged. No approval to deploy or merge implied.

## Release gate

Docker trust verification must PASS; Render requires separate real ingress verification and configuration before being marked ready. SR02 M4 Event branch prerequisite is unchanged.
