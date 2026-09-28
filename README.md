# QuizBlast Enterprise Base v1.0.0 MASTER

This package is the first official MASTER baseline for QuizBlast Enterprise.

## Run

```powershell
copy .env.example .env
# optionally change SECRET_KEY in .env
docker compose down
docker compose up --build
```

Frontend:

```text
http://localhost:5173
```

Backend Swagger:

```text
http://localhost:8001/docs
```

## Backend Deployment Limit

Run exactly one backend process and one backend container. The current Compose
configuration starts one Uvicorn process without `--workers`. Do not increase
`--workers`, start backend replicas, or place multiple backend instances behind
a load balancer with this implementation.

Active room connections, game timers, and broadcasts are held in that process's
memory. PostgreSQL persists room and player state for recovery after a restart;
it does not synchronize live rooms across concurrent processes. Login and
registration rate limits are also process-local. Redis is present in Compose
but is not used to synchronize games or rate limits.

Supporting multiple backend processes requires a separately reviewed design
for shared game transitions, WebSocket delivery, timers, and rate limiting.
Active and host-paused rooms remain available until the host explicitly closes
them; only closed rooms are deleted after 15 days.

## Current Scope

- Register / Login
- Quiz management
- Question management
- Excel/QBDS import preview
- Validation and duplicate detection
- Import Commit
- Import History endpoint
- Host / Player / Display screens
- WebSocket multiplayer
- Leaderboard and podium

## Excel Format

Legacy format:

```text
question | image_url | a | b | c | d | correct | time
```

QBDS format:

```text
QuizName | Category | Language | Audience | Question | Image | OptionA | OptionB | OptionC | OptionD | Correct | Time | Difficulty | QuestionType | Tags | Notes
```

`Correct`: A/B/C/D or 0/1/2/3.

## Development Standard

- MASTER is never edited directly.
- Development proceeds with task IDs such as `QB-233-T001`.
- Each task produces release notes and test results.
- Gate Review and Design Freeze are required before a new MASTER.

## Next Planned Sprint

Sprint 2.3.3 — Enterprise UX.
