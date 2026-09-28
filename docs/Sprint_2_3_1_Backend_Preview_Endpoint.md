# Sprint 2.3.1 — Backend Preview Endpoint

## Amaç

QBDS pipeline'ı ilk kez backend API üzerinden erişilebilir hale getirmek.

## Endpoint

```http
POST /quizzes/{quiz_id}/import/preview
```

## Girdi

- Authorization: Bearer token
- Multipart form-data:
  - file: .xlsx veya .xlsm

## Çıktı

Endpoint database'e yazmaz. Sadece önizleme döndürür.

```json
{
  "mode": "preview_only",
  "filename": "questions.xlsx",
  "quiz_id": 1,
  "mapped_rows": 10,
  "mapping_errors": [],
  "preview_payload": {
    "summary": {
      "preview_rows": 10,
      "importable_rows": 8,
      "blocked_rows": 2
    },
    "preview_rows": []
  },
  "importable_payloads": [],
  "can_continue_to_import": false
}
```

## Kapsam Dışı

- Frontend Preview UI yok.
- Database'e import yok.
- Confirm endpoint yok.

## Test

Swagger:

```text
http://localhost:8001/docs
```

Oradan:

```text
POST /quizzes/{quiz_id}/import/preview
```

endpoint'i test edilebilir.

## Rollback

Endpoint ve `excel_reader.py` kaldırılır. Ana import akışı etkilenmez.
