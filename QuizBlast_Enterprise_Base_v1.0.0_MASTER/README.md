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
