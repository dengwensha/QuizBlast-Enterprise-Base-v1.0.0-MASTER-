# Sprint 2.2.4 — Import Report Engine

## Amaç

Validation Engine sonucunu kullanıcıya, frontend'e ve dosya çıktısına uygun rapor formatına dönüştürmek.

## Eklenen Dosyalar

- backend/app/services/import_report_engine.py
- backend/app/utils/import_report_exporter.py
- backend/app/tests/golden/import_report_cases.json
- backend/app/tests/test_import_report_manual.py

## Çıktılar

- User message
- Frontend JSON payload
- Tablo satırları
- Row-based grouped issues
- JSON export
- CSV export

## Kapsam Dışı

- UI entegrasyonu yapılmadı.
- Excel export için xlsx oluşturma yapılmadı.
- Ana import akışına bağlanmadı.

## Manuel Test

```bash
python -m app.tests.test_import_report_manual
```

## Rollback

Ana sisteme bağlı olmadığı için yeni dosyalar kaldırılarak rollback yapılabilir.
