# CONTENT-01D.12 — Toplu görsel kabul paketi

**Karar:** Teknik taslaklar hazırlanmıştır; **yayın onayı 0/7**, fiziksel test **ertelendi**. Bu dosya bir kabul raporudur, görsellerin tamamlandığı veya canlıya bağlandığı iddiası değildir.

| Set / soru | Kaynak adayı | Otomatik dosya kontrolü | Fiziksel ve editoryal kabul |
| --- | --- | --- | --- |
| Genel Kültür / 11 | `frontend/src/assets/quiz/bosphorus-schematic.svg` | CI SVG denetimi | Bekliyor: coğrafi uygunluk, mobil okunabilirlik |
| Genel Kültür / 12 | Wikimedia Commons, 500×592 aday JPEG; `artwork_thumbnail_candidate_v1.json` | Aday URL/meta doğrulaması | Bekliyor: gerçek URL yüklemesi, hak/atıf, görüntü |
| Genel Kültür / 15 | `frontend/src/assets/quiz/zero-coordinates.svg` | CI SVG denetimi | Bekliyor: 0°/0° harita doğruluğu |
| Bilim ve Teknoloji / 11 | `frontend/src/assets/quiz/series-resistors.svg` | CI SVG denetimi | Bekliyor: devre doğruluğu ve okunabilirlik |
| Bilim ve Teknoloji / 12 | `frontend/src/assets/quiz/planet-orbits.svg` (çap oranlı yeni sürüm) | Çap oranları + CI SVG denetimi | Bekliyor: görüntü, ölçek etiketi, cevap sızması |
| Bilim ve Teknoloji / 13 | `frontend/src/assets/quiz/mitochondrion.svg` | CI SVG denetimi | Bekliyor: biyoloji çizim uygunluğu |
| Bilim ve Teknoloji / 15 | `frontend/src/assets/quiz/binary-place-values.svg` | CI SVG denetimi | Bekliyor: yer değerleri ve cevap ipucu |

## Son toplu testte yapılacaklar

1. Kaynak, lisans, atıf, alternatif metin ve doğru görsel-soru eşleşmesi için editoryal onay.
2. Host Chrome, Player Edge ve Display Opera ekranında görsel yerleşimi, kırpma, okunabilirlik ve geçiş testleri.
3. Bozuk görsel URL'siyle oyun akışının devam etmesi ve açıklayıcı hata gösterimi.
4. Oyunun F5/reconnect/QR akışı ve Host/Admin sınırının korunması.
5. Yalnızca CI, editoryal ve fiziksel kabul tamamlanınca ayrı **CONTENT-01E** yayınlama planı ve kullanıcı onayı.

## Kesin sınırlar

- `visual_assets_review_v1.json` içinde tüm görseller `pending_review`; hiçbir görsel `approved` yapılmadı.
- SVG'ler kaynak dosyalarıdır, istemciye kendiliğinden bağlanmış veya yayınlanmış değildir.
- Wikimedia 500×592 dosyası yalnızca aday URL'dir; indirme ve tarayıcıda yükleme doğrulanmış değildir.
- V3 görsel onay mekanizması gerçek yayınlama yoluna henüz entegre edilmedi.
- Canlı katalog, veritabanı ve Render dağıtımında değişiklik yok.

**Kapanış tanımı:** CONTENT-01D otomatik kalite ve kaynak hazırlığı kapanabilir; **nihai görsel/fiziksel kabul AÇIK** kalır.
