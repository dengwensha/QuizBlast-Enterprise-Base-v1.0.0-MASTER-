# Sprint 2.3.2A — Frontend Import Preview

## Amaç

Frontend Excel import akışını ilk kez yeni backend preview endpoint'e bağlamak.

## Önceki Adım

Sprint 2.3.1 ile backend'e şu endpoint eklendi:

```http
POST /quizzes/{quiz_id}/import/preview
```

## Bu Adımda Yapılan

Admin panelindeki Excel import fonksiyonu artık:

```text
Excel seç
↓
/import/preview endpoint'ine gönder
↓
QBDS Pipeline raporunu al
↓
Alert + console log ile önizleme sonucu göster
```

## Önemli

Bu sürümde database'e kayıt yapılmaz.
Eski direkt import davranışı kaldırıldı.
Import Et / Confirm akışı 2.3.2B sprintinde eklenecek.

## Test

1. Login ol.
2. Quiz seç.
3. Excel Import Ön İzleme alanından QBDS Excel dosyası seç.
4. Popup'ta şu bilgileri gör:
   - Toplam satır
   - Import edilebilir
   - Bloklanan
   - Hata
   - Uyarı
5. Seçili Quiz Soruları listesine yeni soru eklenmemeli.

## Rollback

Bu sürüm sorun çıkarırsa önceki 2.3.1 paketine dönülebilir.
