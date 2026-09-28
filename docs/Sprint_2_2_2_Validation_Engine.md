# Sprint 2.2.2 — Validation Engine Core

## Amaç

QBDS Mapper'dan gelen DTO verilerini database'e gitmeden önce bağımsız bir doğrulama katmanından geçirmek.

## Eklenen Dosyalar

- backend/app/services/validation_engine.py
- backend/app/services/validation_rules.py
- backend/app/services/validation_result.py
- backend/app/services/duplicate_detector.py
- backend/app/tests/golden/golden_validation_rows.json
- backend/app/tests/test_validation_engine_manual.py

## Error Codes

| Kod | Açıklama |
|---|---|
| QB1001 | Question boş |
| QB1002 | Option boş |
| QB1003 | Correct yanlış |
| QB1004 | Time yanlış |
| QB1005 | Duplicate question |
| QB1006 | Difficulty yanlış |
| QB1007 | Language bilinmiyor |
| QB1008 | Duplicate option |
| QB1009 | QuestionType yanlış |

## Kapsam Dışı

Bu sprintte ana Excel import akışına entegrasyon yapılmadı.
Validation Engine bağımsız olarak test edilebilir durumda bırakıldı.

## Manuel Test

Backend container içinde:

```bash
python -m app.tests.test_validation_engine_manual
```

## Rollback

Ana akışa bağlı olmadığı için rollback riski düşüktür.
Yeni eklenen validation dosyaları kaldırılarak geri dönülebilir.
