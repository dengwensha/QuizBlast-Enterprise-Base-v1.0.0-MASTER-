# Sprint 2.2.1 — QBDS Mapper

## Amaç

Excel, AI, manuel giriş ve API kaynaklarından gelen soru verilerini tek bir standart modele dönüştürmek.

## Çıktılar

- `backend/app/schemas/qbds.py`
- `backend/app/services/qbds_mapper.py`
- `backend/app/services/validation_service.py`
- `backend/app/utils/import_report.py`
- Manuel test scripti: `backend/app/tests/test_qbds_mapper_manual.py`

## Kabul Kriterleri

- QBDS Excel kolonları DTO'ya çevrilir.
- Eski Excel formatı geriye dönük desteklenir.
- Correct alanı A/B/C/D veya 0/1/2/3 kabul eder.
- DTO mevcut backend `QuestionCreate` payload formatına çevrilir.
- Validation Engine için ilk temel doğrulama fonksiyonu hazırdır.

## Rollback

Bu modül henüz ana import akışına bağlanmadığı için rollback riski düşüktür.
Sorun olursa `backend/app/schemas`, `backend/app/services`, `backend/app/utils` içindeki yeni dosyalar kaldırılabilir.
