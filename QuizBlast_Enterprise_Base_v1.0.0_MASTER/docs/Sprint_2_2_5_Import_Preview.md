# Sprint 2.2.5 — Import Preview Engine

## Amaç

Validation Engine ve Import Report çıktılarını kullanarak, database'e yazmadan önce kullanıcıya gösterilecek import önizleme payload'ını oluşturmak.

## Bir Önceki Modül

Sprint 2.2.4 — Import Report Engine, validation sonucunu kullanıcı mesajı, frontend payload ve CSV/JSON rapora dönüştürdü.

## Bu Modül Ne Ekler?

Import Preview Engine, her satır için şu bilgileri üretir:

- Row number
- Status: OK / WARNING / ERROR
- Can import
- Question
- Options
- Correct
- Time
- Difficulty
- Issues

## Kapsam Dışı

- React UI entegrasyonu yapılmadı.
- Backend endpoint eklenmedi.
- Database'e yazma yapılmadı.

## Manuel Test

```bash
python -m app.tests.test_import_preview_manual
```

## Sonraki Modül

Sprint 2.2.6 — Import Pipeline Orchestrator

Bu modül Mapper + Validation + Duplicate + Report + Preview modüllerini tek bir servis altında sıralı çalıştıracak. Yine ana sisteme bağlanmayacak; Integration Sprint'ten önce son bağımsız altyapı modülü olacak.
