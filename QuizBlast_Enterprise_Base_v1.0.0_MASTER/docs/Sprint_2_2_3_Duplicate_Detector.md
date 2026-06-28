# Sprint 2.2.3 — Duplicate Detector

## Amaç

QBDS verileri içinde aynı veya çok benzer soruları tespit etmek.

## Bu Sprintte Yapılanlar

- `duplicate_detector.py` geliştirildi.
- Exact duplicate detection eklendi.
- Near duplicate detection için basit Jaccard similarity eklendi.
- Unicode normalize + casefold + noktalama temizleme uygulandı.
- Validation Engine yeni DuplicateMatch yapısına uyumlu hale getirildi.
- Golden duplicate test dataset eklendi.

## Kapsam Dışı

- Database içindeki eski sorularla karşılaştırma yapılmadı.
- Büyük veri için gelişmiş fuzzy matching yapılmadı.
- UI entegrasyonu yapılmadı.

## Kabul Kriterleri

- `Mehmet?` / `mehmet` benzeri case/punctuation farkları normalize edilir.
- Aynı soru tekrarlandığında duplicate warning üretilebilir.
- Yakın benzer sorular Jaccard threshold ile yakalanabilir.
- Ana çalışan sistem etkilenmez.

## Manuel Test

```bash
python -m app.tests.test_duplicate_detector_manual
```

## Rollback

Ana sisteme bağlı olmadığı için yeni `duplicate_detector.py` eski basit sürümle değiştirilebilir.
