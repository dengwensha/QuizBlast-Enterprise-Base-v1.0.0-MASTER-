# Sprint 2.3.2B - Enterprise Import Commit Engine

## Amaç
Preview edilen ve import edilebilir olarak işaretlenen Excel/QBDS satırlarının kullanıcı onayı ile veritabanına aktarılması.

## Eklenenler

### Backend
- `POST /quizzes/{quiz_id}/import/commit`
- `GET /imports/history`
- `ImportHistory` SQLAlchemy modeli
- Import session id üretimi
- Duplicate policy: `skip`
- Tek transaction içinde batch insert
- Başarılı/başarısız import summary response

### Frontend
- Preview sonucunu ekranda saklama
- Preview sonrası `Import Et` butonu
- Import summary kartı
- Başarılı import sonrası quiz ve soru listesini yenileme

## API

### Commit Request
```json
{
  "session_id": "QB-IMP-20260628-AB12CD34",
  "filename": "questions.xlsx",
  "duplicate_policy": "skip",
  "overwrite": false,
  "items": [
    {
      "question": "Soru metni",
      "image_url": "",
      "options": ["A", "B", "C", "D"],
      "correct": 0,
      "time": 15
    }
  ]
}
```

### Commit Response
```json
{
  "success": true,
  "session_id": "QB-IMP-20260628-AB12CD34",
  "imported": 10,
  "skipped": 0,
  "warnings": 0,
  "failed": 0,
  "duration": "0.12s"
}
```

## Notlar
- Bu ilk çalışan sürümde preview data frontend state üzerinden commit endpoint'ine gönderilir.
- Bir sonraki iyileştirmede server-side import session store değerlendirilebilir.
- Büyük dosya ve progress engine sonraki sprintlerde ele alınacaktır.

## Acceptance Criteria Durumu
- Preview sonrası import yapılabiliyor: Tamamlandı
- Transaction kullanılıyor: Tamamlandı
- Import history oluşuyor: Tamamlandı
- Session ID üretiliyor: Tamamlandı
- Import summary gösteriliyor: Tamamlandı
- Rollback davranışı temel seviyede mevcut
- 10.000 satır performans testi henüz yapılmadı
