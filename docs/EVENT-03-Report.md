# EVENT-03 — Etkinlik Raporu

Etkinlik sahibi, tamamlanan oturumun Quiz ve Oturum sayfasından Etkinlik Raporu'nu açar. Final sıralaması oda kaydından bağımsız saklanır. Bu sürümden önce tamamlanan oyunlar için geçmiş rapor oluşturulmaz.

Varsayılan erişim süresi tamamlanmadan itibaren 15 gündür. Süre dolunca erişim kapanır ve periyodik temizlik kaydı siler. Yetkili operatör, süre dolmadan ve kullanıcının talebi üzerine yeni bitiş tarihi verebilir:

```sh
python -m app.services.extend_event_report EVENT_UUID 2026-12-15T18:00:00+03:00
```

Komut, backend ortamında yetkili kabuk erişimi gerektirir. Yeni tarih mevcut bitişten sonra olmalıdır.

Yerel kabul: Yeni etkinlik oturumunu tamamla ve final sıralamasını raporla karşılaştır. Odayı kapatıp uygulamayı yeniden başlat; aynı raporu etkinlik sahibiyle aç. Başka hesapla erişimin reddedildiğini, uzatma sonrası yeni tarihin göründüğünü ve süresi dolan raporun açılmadığını doğrula.
